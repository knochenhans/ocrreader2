from copy import deepcopy

import pytest
from iso639 import Lang  # type: ignore
from tesserocr import PyTessBaseAPI  # type: ignore

from src.ocr_engine.layout_analyzer_tesserocr import LayoutAnalyzerTesserOCR
from src.ocr_engine.ocr_engine_tesserocr import OCREngineTesserOCR
from src.page.ocr_box import OCRBox, TextBox
from src.settings.settings import Settings

langs = [Lang("deu")]
ppi = 300
image_path = "data/1.jpeg"


@pytest.fixture
def project_settings():
    return Settings.from_dict(
        {
            "ppi": 300,
            "langs": ["deu"],
            "paper_size": "a4",
            "export_scaling_factor": 1.2,
            "export_path": "",
            "tesseract_data_path": "/usr/share/tessdata",
            "layout_analyzer": "tesserocr",
        }
    )


def test_tesserocr():
    api = PyTessBaseAPI()
    api.Init(lang="deu+eng")
    api.SetImageFile(image_path)
    box = OCRBox(x=100, y=750, width=230, height=50)
    api.SetRectangle(box.x, box.y, box.width, box.height)
    assert api.GetUTF8Text().strip() == "Startschuß"


def test_general_tesserocr_engine(project_settings):
    ocr_engine = OCREngineTesserOCR(project_settings)
    box = OCRBox(x=100, y=750, width=230, height=50)
    assert ocr_engine.recognize_box_text(image_path, box) == "Startschuß"


def test_general_tesserocr_engine2(project_settings):
    ocr_engine = OCREngineTesserOCR(project_settings)
    box = OCRBox(x=100, y=70, width=200, height=45)
    assert ocr_engine.recognize_box_text(image_path, box) == "EDITORIAL"


# def test_orientation_script(project_settings):
#     ocr_engine = OCREngineTesserOCR(project_settings)
#     result = ocr_engine.detect_orientation_script(image_path)
#     assert result["orientation"] == 0
#     assert result["script"] == 1


def test_analyse_layout(project_settings):
    layout_analyzer = LayoutAnalyzerTesserOCR(project_settings)
    result = layout_analyzer.analyze_layout(image_path)
    assert len(result) == 18

    # expected_result = OCRBox(x=104, y=74, width=193, height=29)
    # box = deepcopy(result[2])
    # assert box.x == expected_result.x
    # assert box.y == expected_result.y
    # assert box.width == expected_result.width
    # assert box.height == expected_result.height

    # if isinstance(box, TextBox):
    #     ocr_engine = OCREngineTesserOCR(project_settings)
    #     assert ocr_engine.recognize_box_text(image_path, box).strip() == "EDITORIAL"
