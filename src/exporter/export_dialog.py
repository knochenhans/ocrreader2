from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
)

from project.project import Project  # type: ignore
from .exporter_widget import ExporterWidget


class ExporterPreviewDialog(QDialog):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)

        self.project = project

        self.setWindowTitle("Exporter Preview")
        self.setGeometry(300, 300, 800, 600)

        self.main_widget = ExporterWidget(self)
        self.main_widget.set_project(self.project)

        layout = QVBoxLayout()
        layout.addWidget(self.main_widget)
        self.setLayout(layout)
