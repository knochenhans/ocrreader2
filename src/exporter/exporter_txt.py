import os
from typing import Dict

from loguru import logger

from exporter.exporter import Exporter  # type: ignore
from page.box_type import BoxType  # type: ignore


class ExporterTxt(Exporter):
    def export_page(self, page_export_data: Dict) -> None:
        logger.info(f"Exporting to TXT file: {self.output_path}")
        try:
            filename = os.path.join(self.output_path, self.filename)
            with open(filename + ".txt", "w") as f:
                for export_data_entry in page_export_data["boxes"]:
                    if export_data_entry["type"] in [
                        BoxType.FLOWING_TEXT,
                        BoxType.HEADING_TEXT,
                        BoxType.PULLOUT_TEXT,
                        BoxType.VERTICAL_TEXT,
                        BoxType.CAPTION_TEXT,
                    ]:
                        logger.info(
                            f"Exporting text of box {export_data_entry["id"]}"
                        )
                        f.write(export_data_entry['ocr_results'].get_text() + "\n")
        except Exception as e:
            logger.error(f"Failed to export to TXT: {e}")
