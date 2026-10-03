import fitz
import re

from dataclasses import dataclass


@dataclass
class Document:
    page_content: str
    metadata: dict

class PDFTextLayerLoader:

    ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
    PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
    ENGLISH_DIGITS = "0123456789"

    ALL_DIGITS = set(
        ARABIC_DIGITS
        + PERSIAN_DIGITS
        + ENGLISH_DIGITS
    )

    def __init__(
        self,
        file_path: str,
        excluded_pages: list[int] | None = None,
    ):
        self.file_path = file_path
        self.excluded_pages = set(excluded_pages or [])

    @classmethod
    def normalize_digits(cls, text: str) -> str:
        translation = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
            "01234567890123456789",
        )

        return text.translate(translation)

    @classmethod
    def reorder_numbers_in_span(cls, span: dict) -> str:
        chars = span.get("chars", [])

        if not chars:
            return span.get("text", "")

        result = []
        i = 0

        while i < len(chars):

            char = chars[i]["c"]

            if char not in cls.ALL_DIGITS:
                result.append(char)
                i += 1
                continue

            number_chars = []

            while (
                i < len(chars)
                and chars[i]["c"] in cls.ALL_DIGITS
            ):
                number_chars.append(chars[i])
                i += 1

            number_chars.sort(
                key=lambda char: char["bbox"][0]
            )

            number = "".join(
                char["c"]
                for char in number_chars
            )

            result.append(number)

        return "".join(result)

    def _extract_page_text(self, page) -> str:
        rawdict = page.get_text("rawdict")

        lines = []

        for block in rawdict["blocks"]:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                line_text = ""

                for span in line["spans"]:
                    fixed_span = self.reorder_numbers_in_span(span)
                    line_text += fixed_span

                if line_text.strip():
                    line_text = self.normalize_digits(line_text)
                    line_text = self.fix_article_header(line_text)

                    lines.append(line_text)

        return "\n".join(lines)

    def load(self):

        pdf = fitz.open(self.file_path)

        documents = []

        try:

            for page_number, page in enumerate(pdf):

                # page_number هنا zero-based
                if page_number in self.excluded_pages:
                    continue

                text = self._extract_page_text(page)

                if not text.strip():
                    continue

                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "page": page_number + 1,
                            "source": self.file_path,
                        },
                    )
                )

        finally:
            pdf.close()

        return documents

    @staticmethod
    def fix_article_header(text: str) -> str:

        pattern = (
            r"(ﻣﺎﺩﺓ|مادة)"
            r"\s*\)"
            r"\s*([0-9٠-٩۰-۹]+)"
            r"\s*\("
            r"\s*:"
        )

        return re.sub(
            pattern,
            r"\1 (\2):",
            text,
        )