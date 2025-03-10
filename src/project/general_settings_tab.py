from typing import Optional
from PySide6.QtGui import QColor, QPalette, Qt, QFont

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QPushButton,
    QColorDialog,
    QFontDialog,
)

from settings import Settings  # type: ignore


class GeneralSettingsTab(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.application_settings: Optional[Settings] = None

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Thumbnail Size Layout
        thumbnail_layout = QHBoxLayout()
        self.thumbnail_size_label = QLabel("Thumbnail Size:", self)
        self.thumbnail_size_edit = QLineEdit(self)
        self.thumbnail_size_edit.textChanged.connect(self.update_thumbnail_size)

        thumbnail_layout.addWidget(self.thumbnail_size_label)
        thumbnail_layout.addWidget(self.thumbnail_size_edit)

        main_layout.addLayout(thumbnail_layout)

        # OCR Editor Group
        ocr_editor_group = QVBoxLayout()
        ocr_editor_group.setAlignment(Qt.AlignmentFlag.AlignTop)
        ocr_editor_label = QLabel("OCR Editor", self)
        ocr_editor_group.addWidget(ocr_editor_label)

        # Merged Word in Dictionary Layout
        in_dict_layout = QHBoxLayout()
        self.merged_word_in_dict_label = QLabel("Merged Word in Dictionary:", self)
        self.merged_word_in_dict_button = self.create_color_button(
            self.choose_color_in_dict
        )

        in_dict_layout.addWidget(self.merged_word_in_dict_label)
        in_dict_layout.addWidget(self.merged_word_in_dict_button)

        ocr_editor_group.addLayout(in_dict_layout)

        # Merged Word not in Dictionary Layout
        not_in_dict_layout = QHBoxLayout()
        self.merged_word_not_in_dict_label = QLabel(
            "Merged Word not in Dictionary:", self
        )
        self.merged_word_not_in_dict_button = self.create_color_button(
            self.choose_color_not_in_dict
        )

        not_in_dict_layout.addWidget(self.merged_word_not_in_dict_label)
        not_in_dict_layout.addWidget(self.merged_word_not_in_dict_button)

        ocr_editor_group.addLayout(not_in_dict_layout)

        # Background Color
        background_color_layout = QHBoxLayout()
        self.background_color_label = QLabel("Background Color:", self)
        self.background_color_button = self.create_color_button(
            self.choose_background_color
        )

        background_color_layout.addWidget(self.background_color_label)
        background_color_layout.addWidget(self.background_color_button)

        ocr_editor_group.addLayout(background_color_layout)

        # Text Color
        text_color_layout = QHBoxLayout()
        self.text_color_label = QLabel("Text Color:", self)
        self.text_color_button = self.create_color_button(self.choose_text_color)

        text_color_layout.addWidget(self.text_color_label)
        text_color_layout.addWidget(self.text_color_button)

        ocr_editor_group.addLayout(text_color_layout)

        main_layout.addLayout(ocr_editor_group)

        # Editor Properties Layout
        editor_properties_layout = QVBoxLayout()
        editor_properties_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        editor_properties_label = QLabel("Box Editor", self)
        editor_properties_layout.addWidget(editor_properties_label)

        # Font Size
        font_size_layout = QHBoxLayout()
        self.font_size_label = QLabel("Font Size:", self)
        self.font_size_button = QPushButton("Choose Font", self)
        self.font_size_button.clicked.connect(self.choose_font)

        font_size_layout.addWidget(self.font_size_label)
        font_size_layout.addWidget(self.font_size_button)

        editor_properties_layout.addLayout(font_size_layout)

        # Box Flow Line Color
        box_flow_line_color_layout = QHBoxLayout()
        self.box_flow_line_color_label = QLabel("Box Flow Line Color:", self)
        self.box_flow_line_color_button = self.create_color_button(
            self.choose_box_flow_line_color
        )

        box_flow_line_color_layout.addWidget(self.box_flow_line_color_label)
        box_flow_line_color_layout.addWidget(self.box_flow_line_color_button)

        editor_properties_layout.addLayout(box_flow_line_color_layout)

        main_layout.addLayout(editor_properties_layout)

        self.setLayout(main_layout)

    def load_settings(self, application_settings: Settings) -> None:
        self.application_settings = application_settings
        self.thumbnail_size_edit.setText(
            str(self.application_settings.get("thumbnail_size", 150))
        )

        # Set default colors if not available in settings
        default_color_in_dict = self.application_settings.get(
            "merged_word_in_dict_color", QColor(0, 255, 0, 255).rgba()
        )
        default_color_not_in_dict = self.application_settings.get(
            "merged_word_not_in_dict_color", QColor(255, 0, 0, 255).rgba()
        )
        default_box_flow_line_color = self.application_settings.get(
            "box_flow_line_color", QColor(0, 0, 255, 255).rgba()
        )

        self.set_button_color(self.merged_word_in_dict_button, default_color_in_dict)
        self.set_button_color(
            self.merged_word_not_in_dict_button, default_color_not_in_dict
        )
        self.set_button_color(
            self.box_flow_line_color_button, default_box_flow_line_color
        )

        # Load editor properties
        background_color = self.application_settings.get(
            "editor_background_color", QColor("white").rgba()
        )
        text_color = self.application_settings.get(
            "editor_text_color", QColor("black").rgba()
        )

        self.set_button_color(self.background_color_button, background_color)
        self.set_button_color(self.text_color_button, text_color)
        self.font_size_label.setText("Font")

    def update_thumbnail_size(self) -> None:
        if self.application_settings:
            thumbnail_size = int(self.thumbnail_size_edit.text())
            self.application_settings.set("thumbnail_size", thumbnail_size)

    def choose_color_in_dict(self) -> None:
        self.choose_color("merged_word_in_dict_color", self.merged_word_in_dict_button)

    def choose_color_not_in_dict(self) -> None:
        self.choose_color(
            "merged_word_not_in_dict_color", self.merged_word_not_in_dict_button
        )

    def choose_background_color(self) -> None:
        self.choose_color("editor_background_color", self.background_color_button)

    def choose_text_color(self) -> None:
        self.choose_color("editor_text_color", self.text_color_button)

    def choose_box_flow_line_color(self) -> None:
        self.choose_color("box_flow_line_color", self.box_flow_line_color_button)

    def choose_color(self, setting_key: str, button: QPushButton) -> None:
        if self.application_settings:
            color = QColorDialog.getColor()
            if color.isValid():
                rgba = color.rgba()
                self.application_settings.set(setting_key, rgba)
                self.set_button_color(button, rgba)

    def choose_font(self) -> None:
        if self.application_settings:
            current_font = self.application_settings.get("editor_font", QFont())
            ok, font = QFontDialog.getFont(current_font, self)
            if ok:
                self.application_settings.set("editor_font", font)

    def set_button_color(self, button: QPushButton, color: int) -> None:
        qcolor = QColor.fromRgb(color)
        palette = button.palette()
        palette.setColor(QPalette.ColorRole.Button, qcolor)
        button.setPalette(palette)
        button.setAutoFillBackground(True)

    def create_color_button(self, slot) -> QPushButton:
        button = QPushButton(self)
        button.setFixedWidth(50)
        button.clicked.connect(slot)
        return button
