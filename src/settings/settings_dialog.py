from typing import Dict, List, Optional

from iso639 import Lang
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from settings.settings import Settings  # type: ignore

from .custom_shortcuts_tab import ShortcutsTab  # type: ignore
from .export_settings_tab import ExportSettingsTab  # type: ignore
from .general_settings_tab import GeneralSettingsTab  # type: ignore
from .project_settings_tab import ProjectSettingsTab  # type: ignore


class SettingsDialog(QDialog):
    settings_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.application_settings: Optional[Settings] = None
        self.project_settings: Optional[Settings] = None
        self.setWindowTitle("Settings")
        self.setGeometry(300, 300, 400, 800)

        layout: QVBoxLayout = QVBoxLayout(self)

        tab_widget: QTabWidget = QTabWidget(self)
        layout.addWidget(tab_widget)

        self.general_settings_tab = GeneralSettingsTab(self)
        self.project_settings_tab = ProjectSettingsTab(self)
        self.shortcuts_tab = ShortcutsTab(self)
        self.export_settings_tab = ExportSettingsTab(self)

        tab_widget.addTab(self.general_settings_tab, "General Options")
        tab_widget.addTab(self.project_settings_tab, "Project Options")
        tab_widget.addTab(self.shortcuts_tab, "Custom Shortcuts")
        tab_widget.addTab(self.export_settings_tab, "Export Options")

        button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(button_box)

        button_box.accepted.connect(self.on_ok_clicked)
        button_box.rejected.connect(self.reject)

    def load_settings(
        self,
        application_settings: Settings,
        project_settings: Settings,
        available_langs: List[Lang],
        custom_shortcuts: Dict[str, str],
    ) -> None:
        self.project_settings = project_settings
        self.application_settings = application_settings
        self.general_settings_tab.load_settings(application_settings)
        self.project_settings_tab.load_settings(project_settings, available_langs)
        self.shortcuts_tab.load_custom_shortcuts(custom_shortcuts)
        self.export_settings_tab.load_settings(application_settings)

    def on_ok_clicked(self) -> None:
        if self.project_settings and self.application_settings:
            self.settings_changed.emit()
            self.project_settings.settings["custom_shortcuts"] = (
                self.shortcuts_tab.set_custom_shortcuts()
            )
            # self.application_settings.settings["box_type_tags"] = (
            #     self.export_settings_tab.get_box_type_tags()
            # )
        self.accept()
