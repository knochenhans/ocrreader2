from typing import Optional, Dict, List
from PySide6.QtCore import Qt, QPointF, QSizeF
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsPixmapItem,
)
from PySide6.QtGui import QPixmap
from loguru import logger

from page_editor.page_editor_controller import PageEditorController  # type: ignore
from page.ocr_box import OCRBox, TextBox  # type: ignore
from page.box_type_color_map import BOX_TYPE_COLOR_MAP  # type: ignore
from page_editor.box_item import BoxItem  # type: ignore
from page.box_type import BoxType  # type: ignore
from page_editor.header_footer_item import HEADER_FOOTER_ITEM_TYPE, HeaderFooterItem  # type: ignore


class PageEditorScene(QGraphicsScene):
    def __init__(self, controller: Optional[PageEditorController] = None) -> None:
        super().__init__()
        self.controller = controller
        self.boxes: Dict[str, BoxItem] = {}
        self.page_image_item: Optional[QGraphicsItem] = None
        self.header_item: Optional[HeaderFooterItem] = None
        self.footer_item: Optional[HeaderFooterItem] = None

    def select_next_box(self) -> None:
        box_items = self.get_all_box_items()
        selected_items = self.get_selected_box_items()

        if len(selected_items) == 0:
            if len(box_items) > 0:
                box_items[0].setSelected(True)
        else:
            selected_index = box_items.index(selected_items[0])
            next_index = (selected_index + 1) % len(box_items)
            selected_items[0].setSelected(False)
            box_items[next_index].setSelected(True)

    def add_box_item_from_ocr_box(self, ocr_box: OCRBox) -> None:
        box_item = BoxItem(ocr_box.id, 0, 0, ocr_box.width, ocr_box.height)
        box_item.set_color(BOX_TYPE_COLOR_MAP[ocr_box.type])

        if self.controller:
            box_item.box_moved.connect(self.on_box_item_moved)
            box_item.box_resized.connect(self.on_box_item_resized)
            box_item.box_right_clicked.connect(self.on_box_item_right_clicked)

        self.addItem(box_item)
        box_item.setPos(ocr_box.x, ocr_box.y)
        box_item.order = ocr_box.order + 1

        if isinstance(ocr_box, TextBox):
            box_item.is_recognized = ocr_box.has_text()
            box_item.has_user_text = ocr_box.user_text != ""

        self.boxes[ocr_box.id] = box_item

    def remove_box_item(self, box_id: str) -> None:
        if box_id in self.boxes:
            self.removeItem(self.boxes[box_id])
            del self.boxes[box_id]

    def on_box_item_moved(self, box_id: str, pos: QPointF) -> None:
        if self.controller:
            logger.debug(f"Page box item {box_id} moved to {pos}")
            ocr_box = self.controller.page.layout.get_ocr_box_by_id(box_id)
            if ocr_box:
                ocr_box.update_position(int(pos.x()), int(pos.y()), "GUI")

    def on_box_item_resized(self, box_id: str, pos: QPointF, size: QPointF) -> None:
        if self.controller:
            logger.debug(
                f"Page box item {box_id} resized by relative position {pos} and size {size}"
            )
            ocr_box = self.controller.page.layout.get_ocr_box_by_id(box_id)
            if ocr_box:
                box_item = self.boxes[box_id]

                new_x = int(box_item.pos().x() + pos.x())
                new_y = int(box_item.pos().y() + pos.y())
                new_width = int(size.x())
                new_height = int(size.y())

                ocr_box.update_position(new_x, new_y, "GUI")
                ocr_box.update_size(new_width, new_height, "GUI")

    def on_box_item_right_clicked(self, box_id: str) -> None:
        logger.debug(f"Page box item {box_id} right clicked")
        selected_items = self.get_selected_box_items()

        # Add the clicked item to the selection if it is not already selected
        if box_id not in [item.box_id for item in selected_items]:
            selected_items.append(self.boxes[box_id])

        # Get ids of all selected boxes
        selected_box_ids = [item.box_id for item in selected_items]
        if self.controller:
            self.controller.show_context_menu(selected_box_ids)

    def get_all_box_items(self) -> List[BoxItem]:
        return [item for item in self.items() if isinstance(item, BoxItem)]

    def get_selected_box_items(self) -> List[BoxItem]:
        return [item for item in self.selectedItems() if isinstance(item, BoxItem)]

    def get_box_under_cursor(self) -> Optional[BoxItem]:
        pos = self.views()[0].mapFromGlobal(QCursor.pos())
        item = self.itemAt(pos, self.views()[0].transform())
        if isinstance(item, BoxItem):
            return item
        return None

    def set_page_image(self, page_pixmap: QPixmap) -> None:
        if self.page_image_item:
            self.removeItem(self.page_image_item)

        self.page_image_item = QGraphicsPixmapItem(page_pixmap)
        self.page_image_item.setZValue(-1)
        self.page_image_item.setCacheMode(
            QGraphicsPixmapItem.CacheMode.DeviceCoordinateCache
        )
        self.page_image_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        self.addItem(self.page_image_item)

    def add_header_footer(self, type: HEADER_FOOTER_ITEM_TYPE, y: float):
        if type is HEADER_FOOTER_ITEM_TYPE.HEADER:
            if self.header_item:
                self.removeItem(self.header_item)
        else:
            if self.footer_item:
                self.removeItem(self.footer_item)

        page_size = QSizeF(self.width(), self.height())
        item = HeaderFooterItem(type, page_size, y)
        self.addItem(item)
        item.setFocus()
        item.update_title()

        if type is HEADER_FOOTER_ITEM_TYPE.HEADER:
            self.header_item = item
        else:
            self.footer_item = item

    def update_header_footer(self, type: HEADER_FOOTER_ITEM_TYPE, y: float):
        if not self.controller:
            return

        if type is HEADER_FOOTER_ITEM_TYPE.HEADER and self.header_item:
            self.header_item.update_bottom_position(y)
            self.controller.set_header(int(y))
        elif type is HEADER_FOOTER_ITEM_TYPE.FOOTER and self.footer_item:
            self.footer_item.update_top_position(y)
            self.controller.set_footer(int(y))
