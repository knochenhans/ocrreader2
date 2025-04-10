import json
import os
import shutil
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from loguru import logger

from ocr_engine.ocr_result import OCRResultBlock  # type: ignore
from ocr_processor import OCRProcessor  # type: ignore
from page.page import Page  # type: ignore
from project.project import Project  # type: ignore
from settings.settings import Settings  # type: ignore


class ProjectManager:
    def __init__(self, project_folder: str) -> None:
        self.projects: List[Tuple[str, str, Optional[datetime]]] = (
            []
        )  # Include modification datetime
        self.current_project: Optional[Project] = None
        self.project_folder = project_folder

        # Ensure the project folder exists
        if not os.path.exists(project_folder):
            logger.info(f"Project folder not found, creating: {project_folder}")
            os.makedirs(project_folder)

        projects = os.listdir(project_folder)

        logger.info(f"Found projects: {len(projects)}")
        logger.info(f"Loading projects from: {project_folder}")

        # Try to load all projects from the project folder
        for folder in projects:
            logger.info(f"Loading project: {folder}")
            uuid = folder
            project_file_path = os.path.join(project_folder, folder, "project.json")

            if os.path.exists(project_file_path):
                with open(project_file_path, "r") as f:
                    project_data = json.load(f)
                project = Project.from_dict(project_data)

                # Parse modification datetime
                modification_date = project_data.get("project", {}).get(
                    "modification_date"
                )
                if modification_date:
                    try:
                        modification_date = datetime.fromisoformat(modification_date)
                    except ValueError:
                        modification_date = None

                self.projects.append((project.name, uuid, modification_date))
                logger.info(f"Loaded project: {project_file_path}")
            else:
                logger.error(
                    f"Empty project folder found: {project_file_path}, removing folder"
                )
                os.rmdir(os.path.join(project_folder, folder))

    def add_project(self, project: Project) -> None:
        modification_date = project.modification_date or datetime.now()
        self.projects.append((project.name, project.uuid, modification_date))

        project_root_path = os.path.join(self.project_folder, project.uuid)

        if not os.path.exists(project_root_path):
            os.makedirs(project_root_path)
        project.folder = project_root_path

    def remove_project(self, index: int) -> None:
        _, project_uuid, _ = self.projects.pop(index)

        project_root_path = os.path.join(self.project_folder, project_uuid)

        if os.path.exists(project_root_path):
            shutil.rmtree(project_root_path)

    def remove_project_by_uuid(self, uuid: str) -> None:
        for index, (_, project_uuid, _) in enumerate(self.projects):
            if project_uuid == uuid:
                self.remove_project(index)
                return

    def get_project_count(self) -> int:
        return len(self.projects)

    def import_project(self, file_path: str) -> str:
        try:
            logger.info(f"Importing project: {file_path}")
            with open(file_path, "r") as f:
                loaded_data = json.load(f)

            project = Project.from_dict(loaded_data)

            logger.info(f"Project pages: {project.get_page_count()}")

            self.add_project(project)
        except Exception as e:
            raise Exception(f"Failed to import project: {e}")

        return project.uuid

    def save_current_project(
        self, progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> None:
        if self.current_project is not None:
            self.save_project_(self.current_project, progress_callback)

    def save_project_(
        self,
        project: Project,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        logger.info(f"Saving project: {project.uuid}")

        self.save_project_pages(project, progress_callback)
        self.save_project_settings(project)

        project_file_path = os.path.join(
            self.project_folder, project.uuid, "project.json"
        )
        project_dict = project.to_dict()

        with open(project_file_path, "w") as f:
            json.dump(project_dict, f)
        logger.info(f"Finished saving project: {project_file_path}")

    def load_project(
        self,
        uuid: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Project:
        project_file_path = os.path.join(self.project_folder, uuid, "project.json")

        if not os.path.exists(project_file_path):
            raise FileNotFoundError(f"Project file not found: {project_file_path}")

        with open(project_file_path, "r") as f:
            loaded_data = json.load(f)
        project = Project.from_dict(loaded_data)
        project.folder = os.path.join(self.project_folder, uuid)

        self.load_project_settings(project)
        self.load_project_pages(project, progress_callback)

        return project

    def load_metadata(self, uuid: str) -> dict:
        project_file_path = os.path.join(self.project_folder, uuid, "project.json")

        if not os.path.exists(project_file_path):
            raise FileNotFoundError(f"Project file not found: {project_file_path}")

        with open(project_file_path, "r") as f:
            loaded_data = json.load(f)

        return loaded_data.get("project", {})

    def save_metadata(self, uuid: str, metadata: dict) -> None:
        project_file_path = os.path.join(self.project_folder, uuid, "project.json")

        if not os.path.exists(project_file_path):
            raise FileNotFoundError(f"Project file not found: {project_file_path}")

        with open(project_file_path, "r") as f:
            existing_data = json.load(f)

        existing_data["project"].update(metadata)

        with open(project_file_path, "w") as f:
            json.dump(existing_data, f)

    def load_project_by_index(self, index: int) -> Project:
        _, uuid, _ = self.projects[index]
        return self.load_project(uuid)

    def load_project_by_uuid(self, uuid: str) -> Project:
        for _, project_uuid, _ in self.projects:
            if project_uuid == uuid:
                return self.load_project(uuid)
        raise ValueError(f"Project with UUID {uuid} not found.")

    def save_project_pages(
        self,
        project: Project,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        pages_folder = os.path.join(self.project_folder, project.uuid, "pages")

        if not os.path.exists(pages_folder):
            os.makedirs(pages_folder)

        # Remove all existing page files
        for file in os.listdir(pages_folder):
            if file.endswith(".json"):
                os.remove(os.path.join(pages_folder, file))

        total_pages = len(project.pages)
        for index, page in enumerate(project.pages):
            page_dict = page.to_dict()
            page_file_path = os.path.join(pages_folder, f"{page.order}.json")
            with open(page_file_path, "w") as f:
                json.dump(page_dict, f)

            if progress_callback:
                progress_callback(index + 1, total_pages, f"Saving page: {page.order}")

        logger.info(f"Finished saving project pages: {pages_folder}")

    def save_project_settings(self, project: Project) -> None:
        if project.settings:
            project.settings.save()

    def load_project_settings(self, project: Project) -> None:
        project.settings = Settings("project_settings", project.folder)
        project.settings.load()

    def load_project_pages(
        self,
        project: Project,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        pages_folder = os.path.join(self.project_folder, project.uuid, "pages")

        if not os.path.exists(pages_folder):
            return

        page_files = [
            file for file in os.listdir(pages_folder) if file.endswith(".json")
        ]
        page_files.sort(key=lambda x: int(os.path.splitext(x)[0]))

        total_pages = len(page_files)
        for index, file in enumerate(page_files):
            with open(os.path.join(pages_folder, file), "r") as f:
                page_dict = json.load(f)
            project.add_page(Page.from_dict(page_dict))

            if progress_callback:
                progress_callback(index + 1, total_pages, f"Loading page: {file}")

        project.set_ocr_processor(OCRProcessor(project.settings))

        logger.info(f"Finished loading project pages: {pages_folder}")

    # TODO: How to deal with the default settings path when the application is installed?
    def new_project(
        self,
        name: str,
        description: str = "",
        default_settings_path="src/data/",
        creation_date: Optional[datetime] = None,
    ) -> Project:
        project = Project(name, description)
        project.creation_date = creation_date or datetime.now()

        project_path = os.path.join(self.project_folder, project.uuid)

        project.settings = Settings(
            "project_settings", project_path, default_settings_path
        )
        project.settings.load()

        self.add_project(project)
        self.save_project_(project)
        return project

    def close_current_project(self) -> None:
        if self.current_project:
            logger.info("Saving OCR results for boxes of project boxes")

            for page in self.current_project.pages:
                if page.layout is None:
                    continue

                for box in page.layout.ocr_boxes:
                    if box.ocr_results is None:
                        continue

                    pages_folder = os.path.join(
                        self.project_folder, self.current_project.uuid
                    )

                    ocr_result_file = os.path.join(
                        pages_folder, "ocr_results", f"{box.id}.json"
                    )

                    if not os.path.exists(os.path.dirname(ocr_result_file)):
                        os.makedirs(os.path.dirname(ocr_result_file))

                    with open(ocr_result_file, "w") as f:
                        json.dump(box.ocr_results.to_dict(), f)
            self.save_current_project

            logger.info(f"Closing project: {self.current_project.uuid}")
            self.current_project = None

    def get_ocr_results_for_page(self, project: Project, page_index: int) -> None:
        if project is None:
            return

        page = next((p for p in project.pages if p.order == page_index), None)
        if page is None:
            logger.info(f"Page with order {page_index} not found in project.")
            return

        ocr_results_folder = os.path.join(project.folder, "ocr_results")

        if not os.path.exists(ocr_results_folder):
            logger.warning(f"OCR results folder not found: {ocr_results_folder}")
            return

        if page.layout is None:
            logger.info(f"Page layout not found for page: {page.order}")
            return

        for box in page.layout.ocr_boxes:
            ocr_result_file = os.path.join(ocr_results_folder, f"{box.id}.json")

            if not os.path.exists(ocr_result_file):
                logger.info(f"OCR result file not found: {ocr_result_file}")
                continue

            with open(ocr_result_file, "r") as f:
                ocr_results = json.load(f)

            if ocr_results is None:
                logger.info(f"OCR results not found for box: {box.id}")
                continue

            box.ocr_results = OCRResultBlock.from_dict(ocr_results)

    def get_page_count(self, project_uuid: str) -> int:
        pages_folder = os.path.join(self.project_folder, project_uuid, "pages")

        if not os.path.exists(pages_folder):
            logger.warning(f"Pages folder not found for project: {project_uuid}")
            return 0

        # Count the number of .json files in the pages folder
        page_files = [
            file for file in os.listdir(pages_folder) if file.endswith(".json")
        ]
        return len(page_files)
