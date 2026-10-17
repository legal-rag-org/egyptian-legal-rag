
import fitz
from dataclasses import dataclass
from typing import Any

from pdf2text_arabic import extract_page


@dataclass
class Document:
    page_content: str
    metadata: dict[str, Any]


class PDF2TextArabicLoader:

    def __init__(
        self,
        file_path: str,
    ):
        self.file_path = file_path

    def load(self) -> list[Document]:

        documents = []

        with fitz.open(self.file_path) as pdf:

            for page_number, page in enumerate(pdf, start=1):

                text, _ = extract_page(
                    page,
                    ocr_strategy="never",
                )

                if not text or not text.strip():
                    continue

                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "page": page_number,
                            "source": self.file_path,
                        },
                    )
                )

        return documents
