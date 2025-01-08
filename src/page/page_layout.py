from typing import List, Optional

from loguru import logger

from page.ocr_box import OCRBox  # type: ignore


class PageLayout:
    def __init__(self, ocr_boxes: List[OCRBox]) -> None:
        self.ocr_boxes: List[OCRBox] = ocr_boxes
        self.region: tuple = (0, 0, 0, 0)  # (x, y, width, height)
        self.header_y: int = 0
        self.footer_y: int = 0

    def get_page_region(self) -> tuple:
        return (
            self.region[0],
            self.header_y,
            self.region[2],
            self.region[3] - self.header_y - self.footer_y,
        )

    def sort_boxes(self) -> None:
        self.ocr_boxes.sort(key=lambda box: box.order)
        self.update_order()

    def update_order(self) -> None:
        for index, box in enumerate(self.ocr_boxes):
            box.order = index

    def move_ocr_box(self, index: int, new_index: int) -> None:
        box_to_move = self.ocr_boxes.pop(index)
        self.ocr_boxes.insert(new_index, box_to_move)
        self.update_order()

    def remove_ocr_box(self, index: int) -> None:
        self.ocr_boxes.pop(index)
        self.update_order()

    def remove_box_by_id(self, box_id: str) -> None:
        for index, box in enumerate(self.ocr_boxes):
            if box.id == box_id:
                self.remove_ocr_box(index)
                return

    def add_ocr_box(self, box: OCRBox, index: Optional[int] = None) -> None:
        if index is None:
            self.ocr_boxes.append(box)
        else:
            self.ocr_boxes.insert(index, box)
        self.update_order()

    def get_ocr_box(self, index: int) -> OCRBox:
        return self.ocr_boxes[index]

    def get_ocr_box_by_id(self, box_id: str) -> Optional[OCRBox]:
        for box in self.ocr_boxes:
            if box.id == box_id:
                return box
        return None

    def replace_ocr_box(self, index: int, box: OCRBox) -> None:
        self.ocr_boxes[index] = box

    def to_dict(self) -> dict:
        return {
            "boxes": [box.to_dict() for box in self.ocr_boxes],
            "region": self.region,
            "header_y": self.header_y,
            "footer_y": self.footer_y,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PageLayout":
        layout = cls([])
        layout.region = data.get("region", (0, 0, 0, 0))
        layout.header_y = data.get("header_y", 0)
        layout.footer_y = data.get("footer_y", 0)
        layout.ocr_boxes = [
            OCRBox.from_dict(box_data) for box_data in data.get("boxes", [])
        ]
        return layout

    def __len__(self) -> int:
        return len(self.ocr_boxes)

    def __iter__(self):
        return iter(self.ocr_boxes)

    def __getitem__(self, index: int) -> OCRBox:
        return self.ocr_boxes[index]

    def __setitem__(self, index: int, box: OCRBox) -> None:
        self.ocr_boxes[index] = box

    def __delitem__(self, index: int) -> None:
        self.ocr_boxes.pop(index)

    def __str__(self) -> str:
        return f"PageLayout(boxes={self.ocr_boxes})"

    def __repr__(self) -> str:
        return self.__str__()
