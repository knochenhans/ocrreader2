import json
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.ocr_processor import OCRProcessor
from src.page.box_type import BoxType
from src.page.ocr_box import BOX_TYPE_MAP, OCRBox
from src.page.page import Page
from src.project.project import Project
from src.settings.settings import Settings

project_settings = Settings.from_dict(
    {
        "ppi": 300,
        "langs": ["deu"],
        "paper_size": "a4",
        "export_scaling_factor": 1.2,
        "export_path": "",
    }
)
image_path = "data/1.jpeg"


def test_save_load_boxes():
    box = OCRBox(x=100, y=750, width=230, height=50)
    box.order = 1
    box.confidence = 0.9
    box.type = BoxType.CAPTION_TEXT

    serialized = box.to_dict()

    with TemporaryDirectory() as temp_dir:
        file_path = f"{temp_dir}/box.json"

        with open(file_path, "w") as f:
            json.dump(serialized, f, indent=4)

        with open(file_path, "r") as f:
            loaded = OCRBox.from_dict(json.load(f))

        assert box.id == loaded.id
        assert box.order == loaded.order
        assert box.confidence == loaded.confidence
        assert box.user_data == loaded.user_data
        assert box.type.value == loaded.type.value
        assert box.x == loaded.x
        assert box.y == loaded.y
        assert box.width == loaded.width
        assert box.height == loaded.height
        assert box == loaded


def test_save_load_boxes2():
    page = Page(image_path, ocr_processor=OCRProcessor(project_settings))
    page.analyze_page(project_settings)
    page.recognize_ocr_boxes()

    with TemporaryDirectory() as temp_dir:
        file_path = f"{temp_dir}/box.json"

        box = page.layout[2]

        with open(file_path, "w") as f:
            json.dump(box.to_dict(), f, indent=4)

        with open(file_path, "r") as f:
            loaded_data = json.load(f)

    box_type = loaded_data["type"]

    if box_type in BOX_TYPE_MAP:
        loaded = BOX_TYPE_MAP[box_type].from_dict(loaded_data)
    else:
        loaded = OCRBox.from_dict(loaded_data)

    TestCase().assertDictEqual(box.to_dict(), loaded.to_dict())

    assert box.id == loaded.id
    assert box.order == loaded.order
    assert box.confidence == loaded.confidence
    assert box.user_data == loaded.user_data
    assert box.type.value == loaded.type.value
    assert box.x == loaded.x
    assert box.y == loaded.y
    assert box.width == loaded.width
    assert box.height == loaded.height


def test_save_load_page():
    page = Page(image_path, ocr_processor=OCRProcessor(project_settings))
    page.analyze_page(project_settings)
    page.recognize_ocr_boxes()

    with TemporaryDirectory() as temp_dir:
        file_path = f"{temp_dir}/page.json"

        with open(file_path, "w") as f:
            json.dump(page.to_dict(), f, indent=4)

        with open(file_path, "r") as f:
            loaded_data = json.load(f)

    loaded = Page.from_dict(loaded_data)

    assert page.image_path == loaded.image_path
    assert page.layout.region == loaded.layout.region
    assert len(page.layout) == len(loaded.layout)

    for box, loaded_box in zip(page.layout, loaded.layout):
        assert box == loaded_box


def test_save_load_project():
    project = Project("Test Project", "A test project")
    project.settings = project_settings
    project.add_image("data/1.jpeg")

    project.set_ocr_processor(OCRProcessor(project_settings))
    project.analyze_pages()
    project.recognize_page_boxes()

    with TemporaryDirectory() as temp_dir:
        project.settings.set("export_path", temp_dir)
        file_path = f"{temp_dir}/project.json"

        with open(file_path, "w") as f:
            json.dump(project.to_dict(), f, indent=4)

        with open(file_path, "r") as f:
            loaded_data = json.load(f)

        loaded = Project.from_dict(loaded_data)

        assert project.uuid == loaded.uuid
        # TestCase().assertDictEqual(
        #     project.settings.to_dict(), loaded.settings.to_dict()
        # )
        # assert len(project.pages) == len(loaded.pages)
