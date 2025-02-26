from PySide6.QtWidgets import QFileDialog
import tempfile

from exporter.export_dialog import ExporterPreviewDialog  # type: ignore


class UserActions:
    def __init__(
        self,
        main_window,
        page_editor_controller,
        project_manager,
        page_icon_view,
        page_editor_view,
    ):
        from main_window.main_window import MainWindow  # type: ignore
        from page_editor.page_editor_controller import PageEditorController  # type: ignore
        from project.project_manager import ProjectManager  # type: ignore
        from main_window.page_icon_view import PagesIconView  # type: ignore
        from page_editor.page_editor_view import PageEditorView  # type: ignore

        self.main_window: MainWindow = main_window
        self.page_editor_controller: PageEditorController = page_editor_controller
        self.project_manager: ProjectManager = project_manager
        self.page_icon_view: PagesIconView = page_icon_view
        self.page_editor_view: PageEditorView = page_editor_view

    def load_images(self, filenames):
        self.main_window.show_status_message(f"Loading images: {filenames}")

        if self.page_editor_controller:
            self.page_editor_controller.open_page()

    def import_pdf(self):
        options = QFileDialog.Option()
        options |= QFileDialog.Option.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Import PDF File",
            "",
            "PDF Files (*.pdf);;All Files (*)",
            options=options,
        )
        if file_name:
            self.main_window.show_status_message(f"Importing PDF: {file_name}")

            if self.project_manager.current_project is not None:
                self.project_manager.current_project.import_pdf(file_name)

    def load_project(self, project_uuid: str):
        self.main_window.show_status_message(f"Loading project: {project_uuid}")

        project = self.project_manager.get_project_by_uuid(project_uuid)

        if not project:
            return

        project.set_settings(self.main_window.project_settings)

        for index, page in enumerate(project.pages):
            page_data = {
                "number": index + 1,
            }
            if page.image_path:
                self.page_icon_view.add_page(page.image_path, page_data)

        self.open_page(0)

    def open_page(self, page_index: int):
        if self.project_manager.current_project is None:
            return

        self.page_icon_view.open_page(page_index)
        self.page_editor_view.set_page(
            self.project_manager.current_project.pages[page_index]
        )

    def open_project(self):
        options = QFileDialog.Option()
        options |= QFileDialog.Option.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Open Project File",
            "",
            "Project Files (*.proj);;All Files (*)",
            options=options,
        )
        if file_name:
            project_uuid = self.project_manager.import_project(file_name)
            self.load_project(project_uuid)

    def save_project(self):
        self.main_window.show_status_message("Saving project")
        self.project_manager.save_current_project()
        self.main_window.show_status_message("Project saved")

    def export_project(self):
        self.main_window.show_status_message("Exporting project")
        project = self.project_manager.current_project

        if not project:
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            exporter_dialog = ExporterPreviewDialog(project, self.main_window)
            exporter_dialog.exec()

    def analyze_layout(self):
        self.main_window.show_status_message("Analyzing layout")
        controller = self.main_window.page_editor_view.page_editor_scene.controller

        if not controller:
            return

        current_page = controller.page
        current_page.analyze_page()

        for box in current_page.layout.ocr_boxes:
            controller.add_page_box_item_from_ocr_box(box)

    def recognize_boxes(self):
        self.main_window.show_status_message("Recognizing OCR boxes")
        controller = self.main_window.page_editor_view.page_editor_scene.controller

        if not controller:
            return

        current_page = controller.page
        current_page.recognize_ocr_boxes()
        self.ocr_editor()

    def analyze_layout_and_recognize(self):
        self.main_window.show_status_message("Analyzing layout and recognizing")
        controller = self.main_window.page_editor_view.page_editor_scene.controller

        if not controller:
            return

        current_page = controller.page
        current_page.analyze_page()
        current_page.recognize_ocr_boxes()

    def ocr_editor(self):
        self.main_window.show_status_message("Removing line breaks")
        controller = self.main_window.page_editor_view.page_editor_scene.controller

        if not controller:
            return

        controller.ocr_editor(True)

    def set_header_footer_for_project(self):
        controller = self.main_window.page_editor_view.page_editor_scene.controller

        if not controller:
            return

        project = self.project_manager.current_project

        if not project:
            return

        for page in project.pages:
            page.set_header(controller.page.layout.header_y)
            page.set_footer(controller.page.layout.footer_y)

    # def place_recognition_box(self):
    #     self.main_window.page_editor_view
