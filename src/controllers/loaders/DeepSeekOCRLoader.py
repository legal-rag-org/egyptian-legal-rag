import base64
import logging

import fitz
from dataclasses import dataclass
from typing import Any


@dataclass
class OCRDocument:
    page_content: str
    metadata: dict[str, Any]


class DeepSeekOCRLoader:

    def __init__(
        self,
        file_path: str,
        ocr_client,
        dpi: int = 200,
        excluded_pages: list[int] | None = None,
    ):
        self.file_path = file_path
        self.ocr_client = ocr_client
        self.dpi = dpi
        self.excluded_pages = set(excluded_pages or [])
        self.logger = logging.getLogger("uvicorn.error")

    def normalize_arabic_digits(self, text: str) -> str:
        translation_table = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
            "01234567890123456789",
        )
        return text.translate(translation_table)

    async def aload(self) -> list[OCRDocument]:
        documents = []
        zoom = self.dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        with fitz.open(self.file_path) as pdf:
            for page_number, page in enumerate(pdf):
                if page_number in self.excluded_pages:
                    continue

                pix = page.get_pixmap(
                    matrix=matrix,
                    alpha=False,
                )

                image_bytes = pix.tobytes("png")
                image_base64 = base64.b64encode(
                    image_bytes
                ).decode("utf-8")

                text = await self.ocr_client.generate_with_image(
                    prompt="<|grounding|>Convert this document page to Markdown. Extract only the visible document content. Do not output chat tokens or repeat the prompt.",
                    image_base64=image_base64,
                    image_mime_type="image/png",
                )

                if not text or not text.strip():
                    self.logger.warning(
                        "DeepSeek OCR returned empty text for page %s",
                        page_number + 1,
                    )
                    continue

                text = self.normalize_arabic_digits(text)

                documents.append(
                    OCRDocument(
                        page_content=text.strip(),
                        metadata={
                            "page": page_number + 1,
                            "source": self.file_path,
                        },
                    )
                )

        return documents
