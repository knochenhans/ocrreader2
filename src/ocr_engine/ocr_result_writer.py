from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from ocr_engine.ocr_result import OCRResultBlock, OCRResultSymbol, OCRResultWord  # type: ignore
from settings import Settings  # type: ignore
import aspell  # type: ignore
from bs4 import BeautifulSoup


class TextPartType(Enum):
    TEXT = 0
    HYPHENATED_WORD = 1


@dataclass
class TextPart:
    part_type: TextPartType
    text: str
    word_first_part_with_hyphen: str
    word_second_part: str


class OCRResultWriter:
    def __init__(
        self,
        application_settings: Settings,
        lang: str,
        blacklist: Optional[List[str]] = None,
    ) -> None:
        self.application_settings = application_settings
        self.text_parts: List[TextPart] = []
        self.buffer_word: bool = False
        self.word_first_part_with_hyphen = ""
        self.word_first_part_hyphenized = ""

        self.lang = lang
        self.blacklist = blacklist

        self.spell = aspell.Speller("lang", self.lang)

    def _check_hyphenated_word(self, first_part: str, second_part: str) -> bool:
        # Strip the HTML tags using BeautifulSoup
        first_part_stripped = (
            BeautifulSoup(first_part, "html.parser").get_text().strip()
        )
        second_part_stripped = (
            BeautifulSoup(second_part, "html.parser").get_text().strip()
        )

        if self.blacklist is not None:
            # Check if the second part is in the blacklist
            if second_part_stripped.lower() in self.blacklist:
                return False

        # Check if the second part starts with a capital letter
        if second_part_stripped[0].isupper():
            return False

        # TODO: Disable spell checking for now
        # return self._check_spelling(first_part_stripped + second_part_stripped)
        return True

    def _check_spelling(self, word: str) -> bool:
        # Remove non-alphanumeric characters for checking
        word = "".join(e for e in word if e.isalnum())
        return self.spell.check(word)

    def _set_confidence_color_background(
        self,
        format: QTextCharFormat,
        element: OCRResultWord | OCRResultSymbol,
        confidence_color_threshold: int,
    ) -> None:
        if element.confidence < confidence_color_threshold:
            format.setBackground(
                QColor(*element.get_confidence_color(confidence_color_threshold))
            )

    def _write_word_symbols(
        self,
        text_parts: List[TextPart],
        cursor: QTextCursor,
        symbols: list,
        confidence_color_threshold: int,
        word_format: QTextCharFormat,
        is_hyphenated_word: bool = False,
    ) -> None:
        for i, symbol in enumerate(symbols):
            symbol_format = QTextCharFormat(
                word_format
            )  # Inherit word-level formatting
            self._set_confidence_color_background(
                symbol_format, symbol, confidence_color_threshold
            )
            cursor.insertText(symbol.get_text(), symbol_format)

            # Check if next symbol is a hyphen and this is the last symbol in the word
            if is_hyphenated_word:
                if i < len(symbols) - 1:
                    if symbols[i + 1].get_text() == "-":
                        self.word_first_part_with_hyphen = self.document.toHtml()
                else:
                    if self.word_first_part_hyphenized == "":
                        self.word_first_part_hyphenized = self.document.toHtml()

        if is_hyphenated_word:
            if self.buffer_word:
                # Store the the first and last part of the hyphenated word
                text_parts.append(
                    self._store_document_state(
                        TextPartType.HYPHENATED_WORD,
                        self.word_first_part_with_hyphen,
                        self.word_first_part_hyphenized,
                        self.document.toHtml(),
                    )
                )
                self.word_first_part_with_hyphen = ""
                self.word_first_part_hyphenized = ""
                self.buffer_word = False
            else:
                self.buffer_word = True
                self._reset_document()

    def _reset_document(self) -> None:
        self.document = QTextDocument()
        self.cursor = QTextCursor(self.document)
        self.cursor.movePosition(QTextCursor.MoveOperation.Start)

    def _store_document_state(
        self,
        type: TextPartType,
        text: str = "",
        word_first_part_unhyphenized: str = "",
        word_second_part: str = "",
    ) -> TextPart:
        part = TextPart(type, text, word_first_part_unhyphenized, word_second_part)

        self._reset_document()

        return part

    def _ocr_to_text_parts(
        self, ocr_result_blocks: list[OCRResultBlock]
    ) -> List[TextPart]:
        self._reset_document()

        confidence_color_threshold = self.application_settings.get(
            "confidence_color_threshold", 50
        )

        text_parts = []

        first_block = True
        for block in ocr_result_blocks:
            if not first_block:
                self.cursor.insertBlock()

            first_block = False
            first_paragraph = True
            is_hyphenated_word = False

            for paragraph in block.paragraphs:
                if not first_paragraph:
                    self.cursor.insertBlock()
                first_paragraph = False

                for l, line in enumerate(paragraph.lines):
                    for w, word in enumerate(line.words):
                        # Fallback if no symbols are present
                        if len(word.symbols) == 0:
                            self.cursor.insertText(word.text, QTextCharFormat())
                            continue

                        # Look ahead to check if the current word is the first or last word of a line
                        if w == len(line.words) - 1 and l < len(paragraph.lines) - 1:
                            # ... and if it ends with a hyphen
                            if word.symbols[-1].get_text() == "-":
                                text_parts.append(
                                    self._store_document_state(
                                        TextPartType.TEXT, self.document.toHtml()
                                    )
                                )
                                is_hyphenated_word = True

                        word_format = QTextCharFormat()
                        self._set_confidence_color_background(
                            word_format, word, confidence_color_threshold
                        )

                        self._write_word_symbols(
                            text_parts,
                            self.cursor,
                            word.symbols,
                            confidence_color_threshold,
                            word_format,
                            is_hyphenated_word,
                        )

                        if w == 0 and not self.buffer_word:
                            # Beginning of the next line, so this is the second part of the hyphenated word
                            is_hyphenated_word = False

                        if word != line.words[-1]:
                            self.cursor.insertText(" ", QTextCharFormat())
                    if line != paragraph.lines[-1] and not is_hyphenated_word:
                        self.cursor.insertText(" ", QTextCharFormat())
            if block != ocr_result_blocks[-1]:
                self.cursor.insertText("\n", QTextCharFormat())

        # Append the last part
        text_parts.append(
            self._store_document_state(TextPartType.TEXT, self.document.toHtml())
        )

        return text_parts

    def _text_parts_to_qdocument(self, text_parts: List[TextPart]) -> QTextDocument:
        document = QTextDocument()
        cursor = QTextCursor(document)

        merged_word_in_dict_color = self.application_settings.get(
            "merged_word_in_dict_color", QColor(0, 255, 0, 255).rgba()
        )
        merged_word_not_in_dict_color = self.application_settings.get(
            "merged_word_not_in_dict_color", QColor(255, 0, 0, 255).rgba()
        )

        # Merge the parts
        for text_part in text_parts:
            if text_part.part_type == TextPartType.TEXT:
                cursor.insertHtml(text_part.text)
            elif text_part.part_type == TextPartType.HYPHENATED_WORD:
                start_position = cursor.position()
                if self._check_hyphenated_word(
                    text_part.word_first_part_with_hyphen, text_part.word_second_part
                ):
                    cursor.insertHtml(text_part.text)
                    cursor.insertHtml(text_part.word_second_part)
                    text_color = QColor(merged_word_in_dict_color)
                else:
                    cursor.insertHtml(text_part.word_first_part_with_hyphen)
                    cursor.insertText(" ")
                    cursor.insertHtml(text_part.word_second_part)
                    text_color = QColor(merged_word_not_in_dict_color)

                # Apply text color for the hyphenated word
                text_color_format = QTextCharFormat()
                text_color_format.setForeground(text_color)

                # Select all text after the saved position
                cursor.setPosition(start_position, QTextCursor.MoveMode.KeepAnchor)
                cursor.mergeCharFormat(text_color_format)
                cursor.movePosition(QTextCursor.MoveOperation.End)
        return document

    def to_qdocument(self, ocr_result_blocks: list[OCRResultBlock]) -> QTextDocument:
        text_parts = self._ocr_to_text_parts(ocr_result_blocks)

        return self._text_parts_to_qdocument(text_parts)
