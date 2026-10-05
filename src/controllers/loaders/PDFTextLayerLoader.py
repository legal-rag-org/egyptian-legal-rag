import fitz
from dataclasses import dataclass


@dataclass
class Document:
    page_content: str
    metadata: dict


class PDFTextLayerLoader:

    def __init__(
        self,
        file_path: str,
        excluded_pages: list[int] | None = None,
    ):
        self.file_path = file_path
        self.excluded_pages = set(excluded_pages or [])

    def load(self):
        pdf = fitz.open(self.file_path)
        documents = []

        try:
            for page_number, page in enumerate(pdf):

                # page_number is zero-based
                # if page_number in self.excluded_pages:
                #     continue

                text = page.get_text("text")

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