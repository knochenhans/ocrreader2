from tempfile import TemporaryDirectory
from typing import Callable, List, Optional

import numpy as np  # type: ignore
from loguru import logger

from ocr_processor import OCRProcessor  # type: ignore
from page.box_type import BoxType  # type: ignore
from page.image_preprocessor import ImagePreprocessor  # type: ignore
from page.ocr_box import BOX_TYPE_MAP, OCRBox, TextBox  # type: ignore
from page.page_layout import PageLayout  # type: ignore
from settings.settings import Settings  # type: ignore


class Page:
    def __init__(
        self,
        image_path: Optional[str] = None,
        order: int = 0,
        ocr_processor: Optional[OCRProcessor] = None,
    ) -> None:
        self.image_path = image_path
        self.order = order
        self.ocr_processor = ocr_processor
        self.layout = PageLayout([])
        self.image: Optional[np.ndarray] = None

    def analyze_page(
        self,
        project_settings: Settings,
        region: Optional[tuple[int, int, int, int]] = None,
        keep_existing_boxes: bool = False,
        filter_by_box_types: bool = True,
        filter_by_size: bool = True,
    ) -> List[OCRBox]:
        if not self.image_path:
            logger.error("No image path set for page")
            return []

        if region is None:
            # Load and get the region from the image
            image_processor = ImagePreprocessor(self.image_path)
            self.layout.set_region(image_processor.get_image_size())
            region = self.layout.get_final_page_region()

        if self.ocr_processor:
            ocr_boxes = self.ocr_processor.analyze_layout(self.image_path, region)
        else:
            raise Exception("No OCR processor set for page")

        if project_settings:
            # Filter by box types if enabled
            if filter_by_box_types:
                box_types = project_settings.get("box_types")
                if box_types is not None:
                    filtered_boxes = []
                    for box in ocr_boxes:
                        if box.type.value in box_types:
                            filtered_boxes.append(box)
                    ocr_boxes = filtered_boxes

            # Filter by size if enabled
            if filter_by_size:
                x_size_threshold = project_settings.get("x_size_threshold") or 0
                y_size_threshold = project_settings.get("y_size_threshold") or 0
                if x_size_threshold > 0 or y_size_threshold > 0:
                    ocr_boxes = [
                        box
                        for box in ocr_boxes
                        if box.width >= x_size_threshold
                        and box.height >= y_size_threshold
                    ]

        # Get new order numbers for the boxes
        max_order = max([box.order for box in self.layout.ocr_boxes], default=-1)
        for box in ocr_boxes:
            max_order += 1
            box.order = max_order

        if keep_existing_boxes:
            self.layout.ocr_boxes += ocr_boxes
        else:
            self.layout.ocr_boxes = ocr_boxes
        self.layout.sort_ocr_boxes_by_order()
        return ocr_boxes

    def is_valid_box_index(self, box_index: int) -> bool:
        return box_index >= 0 and box_index < len(self.layout.ocr_boxes)

    def analyze_region(self, region: tuple[int, int, int, int]) -> List[OCRBox]:
        if not self.image_path:
            logger.error("No image path set for page")
            return []

        if self.ocr_processor:
            return self.ocr_processor.analyze_layout(self.image_path, region)
        else:
            raise Exception("No OCR processor set for page")

    def analyze_ocr_box_(self, box_index: int) -> List[OCRBox]:
        if not self.is_valid_box_index(box_index):
            logger.error("Invalid ocr_box index: %d", box_index)
            return []

        region = self.layout.ocr_boxes[box_index]

        try:
            return self.analyze_region(
                (region.x, region.y, region.width, region.height)
            )
        except Exception as e:
            logger.error(
                "Error analyzing layout for ocr_box at index %d: %s", box_index, e
            )
            return []

    def analyze_ocr_box(self, ocr_box_index: int) -> None:
        recognized_boxes = self.analyze_ocr_box_(ocr_box_index)

        if len(recognized_boxes) == 1:
            # Keep some data from the original box
            recognized_boxes[0].id = self.layout.ocr_boxes[ocr_box_index].id
            recognized_boxes[0].order = self.layout.ocr_boxes[ocr_box_index].order
            recognized_boxes[0]._callbacks = self.layout.ocr_boxes[
                ocr_box_index
            ]._callbacks
            recognized_boxes[0].user_data = self.layout.ocr_boxes[
                ocr_box_index
            ].user_data
            self.layout.ocr_boxes[ocr_box_index] = recognized_boxes[0]
            recognized_boxes[0].notify_callbacks("Backend")
        else:
            self.layout.remove_ocr_box(ocr_box_index)
            for recognized_box in recognized_boxes:
                self.layout.add_ocr_box(recognized_box)

    def align_ocr_box(self, ocr_box_index: int) -> None:
        recognized_boxes = self.analyze_ocr_box_(ocr_box_index)

        if len(recognized_boxes) > 0:
            best_box = None

            for recognized_box in recognized_boxes:
                if best_box is None:
                    best_box = recognized_box
                elif recognized_box.similarity(
                    self.layout.ocr_boxes[ocr_box_index]
                ) > best_box.similarity(self.layout.ocr_boxes[ocr_box_index]):
                    best_box = recognized_box

            if best_box is not None:
                self.layout.ocr_boxes[ocr_box_index].x = best_box.x
                self.layout.ocr_boxes[ocr_box_index].y = best_box.y
                self.layout.ocr_boxes[ocr_box_index].width = best_box.width
                self.layout.ocr_boxes[ocr_box_index].height = best_box.height
        else:
            self.layout.remove_ocr_box(ocr_box_index)

    def recognize_ocr_boxes(
        self,
        box_index: Optional[int] = None,
        convert_empty_textboxes: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        if not self.image_path:
            logger.error("No image path set for page")
            return

        if box_index is not None:
            if not self.is_valid_box_index(box_index):
                logger.error("Invalid ocr_box index: %d", box_index)
                return

            boxes_to_recognize = [self.layout.ocr_boxes[box_index]]
        else:
            boxes_to_recognize = self.layout.ocr_boxes

        image_boxes = [
            box
            for box in boxes_to_recognize
            if isinstance(box, OCRBox)
            and not isinstance(box, TextBox)
            and box.type == BoxType.IGNORE
        ]

        image_processor = ImagePreprocessor(self.image_path)

        # Create a temporary directory for output
        with TemporaryDirectory() as temp_dir:
            # Erase the image boxes from the image
            erased_image_path = image_processor.erase_boxes(
                [(box.x, box.y, box.width, box.height) for box in image_boxes],
                temp_dir,
            )

            if self.ocr_processor:
                self.ocr_processor.recognize_boxes(
                    erased_image_path, boxes_to_recognize, progress_callback
                )
            else:
                raise Exception("No OCR processor set for page")

        logger.info(f"Recognized boxes: {boxes_to_recognize}")

        if convert_empty_textboxes and box_index is None:
            # Convert empty TextBoxes to ImageBoxes
            for i, ocr_box in enumerate(self.layout.ocr_boxes):
                if isinstance(ocr_box, TextBox):
                    if not ocr_box.has_text():
                        self.convert_ocr_box(i, BoxType.FLOWING_IMAGE)

        # Notify callbacks for recognized boxes
        for ocr_box in boxes_to_recognize:
            ocr_box.notify_callbacks("Backend")

            if isinstance(ocr_box, TextBox):
                ocr_box.user_text = ""

    def convert_ocr_box(self, box_index: int, box_type: BoxType) -> None:
        if not self.is_valid_box_index(box_index):
            logger.error("Invalid ocr_box index: %d", box_index)
            return

        ocr_box = self.layout.ocr_boxes[box_index]
        new_box = ocr_box.convert_to(box_type)
        self.layout.ocr_boxes[box_index] = new_box

    def generate_page_export_data(self, project_settings: Settings) -> dict:
        if project_settings is None:
            raise Exception("No project settings set for page")

        langs = project_settings.get("langs") or ["eng"]

        export_data = {
            "image_path": self.image_path,
            "order": self.order,
            "lang": langs[0],
            "boxes": [],
        }

        for ocr_box in self.layout.ocr_boxes:
            export_data_entry = {
                "id": ocr_box.id,
                "order": ocr_box.order,
                "position": ocr_box.position(),
                "type": ocr_box.type,
                "user_data": ocr_box.user_data,
                "confidence": ocr_box.confidence,
                "ocr_results": ocr_box.ocr_results,
            }

            if isinstance(ocr_box, TextBox):
                export_data_entry["user_text"] = ocr_box.user_text.strip()
                export_data_entry["flows_into_next"] = ocr_box.flows_into_next

            export_data["boxes"].append(export_data_entry)

        return export_data

    def set_header(self, header: int) -> None:
        self.layout.header_y = header

    def set_footer(self, footer: int) -> None:
        self.layout.footer_y = footer

    def to_dict(self) -> dict:
        data = {
            "page": {
                "image_path": self.image_path,
                "order": self.order,
                "layout": self.layout.to_dict(),
            },
        }

        return data

    def merge_ocr_box_with_ocr_box(self, index1: int, index2: int) -> None:
        if not self.is_valid_box_index(index1) or not self.is_valid_box_index(index2):
            logger.error("Invalid ocr_box index: %d or %d", index1, index2)
            return

        ocr_box1 = self.layout.ocr_boxes[index1]
        ocr_box2 = self.layout.ocr_boxes[index2]

        # Merge second box into first box, then remove second box
        ocr_box1.x = min(ocr_box1.x, ocr_box2.x)
        ocr_box1.y = min(ocr_box1.y, ocr_box2.y)
        ocr_box1.width = (
            max(ocr_box1.x + ocr_box1.width, ocr_box2.x + ocr_box2.width) - ocr_box1.x
        )
        ocr_box1.height = (
            max(ocr_box1.y + ocr_box1.height, ocr_box2.y + ocr_box2.height) - ocr_box1.y
        )

        ocr_box1.confidence = max(ocr_box1.confidence, ocr_box2.confidence)
        ocr_box1.user_data.update(ocr_box2.user_data)

        if ocr_box1.ocr_results and ocr_box2.ocr_results:
            ocr_box1.ocr_results.paragraphs.extend(ocr_box2.ocr_results.paragraphs)

        if isinstance(ocr_box1, TextBox) and isinstance(ocr_box2, TextBox):
            ocr_box1.user_text += " " + ocr_box2.user_text
            ocr_box1.flows_into_next = ocr_box2.flows_into_next

        self.layout.ocr_boxes.remove(ocr_box2)
        ocr_box1.notify_callbacks("Backend")

        logger.info(f"Merged box {ocr_box2.id} into {ocr_box1.id}")

    @classmethod
    def from_dict(cls, data: dict) -> "Page":
        page_data = data["page"]

        page = cls(
            page_data["image_path"],
            order=page_data.get("order", 0),
        )

        for box_data in page_data["layout"]["boxes"]:
            box_type = box_data["type"]

            if box_type in BOX_TYPE_MAP:
                ocr_box = BOX_TYPE_MAP[box_type].from_dict(box_data)
            else:
                ocr_box = OCRBox.from_dict(box_data)

            page.layout.add_ocr_box(ocr_box)

        page.layout.region = tuple(page_data["layout"]["region"])
        page.layout.header_y = page_data["layout"].get("header_y", 0)
        page.layout.footer_y = page_data["layout"].get("footer_y", 0)

        return page
