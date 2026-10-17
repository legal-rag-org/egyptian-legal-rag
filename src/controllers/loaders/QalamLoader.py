from dataclasses import dataclass
from typing import Any

import qalam


@dataclass
class Document:
    page_content: str
    metadata: dict[str, Any]


class QalamLoader:

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:

        documents = []

        doc = qalam.Document(self.file_path)

        for page in doc:

            text = page.text

            if not text or not text.strip():
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "page": page.number,
                        "source": self.file_path,
                    },
                )
            )

        return documents