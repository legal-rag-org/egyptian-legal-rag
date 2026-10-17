import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from langchain_community.document_loaders import TextLoader

from models import ProcessingEnum

from .BaseController import BaseController
from .ProjectController import ProjectController
from .enums.process import ProcessControllerEnums
from .loaders import PDFTableDetector, TableLoader, PDFTextLayerLoader, PDF2TextArabicLoader, QalamLoader

import qalam

ARTICLE_WORDS = r"(?:المادة|الماده|مادة|ماده)"
ORDINALS = (
    r"(?:الأولى|الأولي|الاولى|الاولي|الثانية|الثانيه|الثالثة|الثالثه|"
    r"الرابعة|الرابعه|الخامسة|الخامسه|السادسة|السادسه|"
    r"السابعة|السابعه|الثامنة|الثامنه|التاسعة|التاسعه|العاشرة|العاشره)"
)
NUM = r"[0-9٠-٩۰-۹]+"

ARTICLE_PATTERN = re.compile(
    rf"""
    ^[ \t]*[()\[\]]*[ \t]*
    {ARTICLE_WORDS}
    [ \t]*[()\[\]]*[ \t]*
    (?:رقم[ \t]*)?
    ({NUM}|{ORDINALS})
    [ \t]*[()\[\]:.\-]*[ \t]*$
    """,
    re.MULTILINE | re.VERBOSE,
)

@dataclass
class Document:
    page_content : str
    metadata: dict[str, Any]

class ProcessController(BaseController):
    def __init__(self, project_id: str, vision_model):
        super().__init__()

        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)
        self.logger = logging.getLogger("uvicorn.error")
        self.vision_model = vision_model


    def get_file_extension(self, file_id: str):
        file_ext = os.path.splitext(file_id)[-1]

        return file_ext

    
    def get_file_loader(self, file_id: str):
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.isfile(file_path):
            self.logger.warning("File not found: %s", file_id)
            return None

        file_ext = self.get_file_extension(file_id).lower()

        loaders = {
            ProcessingEnum.TXT.value: lambda: TextLoader(
                file_path, encoding="utf-8"
            ),
            ProcessingEnum.PDF.value: lambda: PDFTextLayerLoader(file_path),
        }

        loader_factory = loaders.get(file_ext)
        return loader_factory() if loader_factory else None


    def get_file_content(self, file_id: str):

        loader = self.get_file_loader(file_id=file_id)

        if loader:
         return loader.load()

        return None

    def clean_arabic(self, text: str) -> str:
        text = text.replace("ی", "ي").replace("ک", "ك")
        text = self.normalize_digits(text)
        lines = [
            l for l in text.splitlines()
            if not re.search(r"(.)\1{2,}", l.replace(" ", "")) or len(l) > 60
        ]
        return "\n".join(lines)

    def normalize_text(self, text: str) -> str:
        text = self.clean_arabic(text)
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) >= 1]
        return "\n".join(lines)

    async def process_file_content(self, file_id: str,
                             chunk_size: int=1000, overlap_size: int=100):


        file_ext = self.get_file_extension(file_id=file_id)

        if file_ext == ProcessingEnum.PDF.value:
            return await self.process_pdf(
                file_id=file_id,
                chunk_size=chunk_size,
                overlap_size=overlap_size
            )

        if file_ext == ProcessingEnum.TXT.value:
            return self.process_text(
                file_id=file_id,
                chunk_size=chunk_size,
                overlap_size=overlap_size
            )

    def split_by_article_marker(self, text: str): 
        pattern = re.compile(
            r'(?im)^\s*'
            r'\(?\s*'
            r'(?:المادة|الماده|مادة|ماده)'
            r'\s*'
            r'(?:رقم\s*)?'
            r'(?:'
                r'\(\s*([0-9٠-٩۰-۹]+)\s*\)'
                r'|'
                r'([0-9٠-٩۰-۹]+)'
                r'|'
                r'(الأولى|الأولي|الثانية|الثانيه|الثالثة|الثالثه|'
                r'الرابعة|الرابعه|الخامسة|الخامسه|السادسة|السادسه|'
                r'السابعة|السابعه|الثامنة|الثامنه|التاسعة|التاسعه|'
                r'العاشرة|العاشره)'
            r')'
            r'\s*\)?'
            r'\s*:?\s*$'
        )

        matches = list(pattern.finditer(text))

        if not matches:
            return []

        chunks = []

        for index, match in enumerate(matches):

            article_number = (
                match.group(1)
                or match.group(2)
                or match.group(3)
            )

            start = match.start()

            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            )

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    (
                        article_number,
                        chunk_text
                    )
                )

        return chunks

    def process_text(
        self,
        file_id: str,
        chunk_size: int = 1000,
        overlap_size: int = 100
    ):
        base_metadata = ProcessControllerEnums.BASE_METADATA.value

        file_content = self.get_file_content(
            file_id=file_id
        )

        if file_content is None:
            self.logger.error(
                f"Error While processing {file_id}"
            )
            return None

        documents = []

        for page in file_content:

            text = self.normalize_text(
                text=page.page_content
            )

            if not text:
                continue

            
            articles = self.split_by_article_marker(text)

            # Fallback for text without article markers
            if not articles:
                chunks = self._sliding_window(
                    text=text,
                    chunk_size=chunk_size,
                    overlap_size=overlap_size,
                )

                metadata = {
                    **base_metadata,
                    "article": "unknown",
                    "content_type": "text",
                }

                for chunk in chunks:
                    documents.append(
                        Document(
                            page_content=chunk.strip(),
                            metadata=metadata.copy(),
                        )
                    )

                continue

            for article_number, article_text in articles:


                metadata = {
                    **base_metadata,
                    "article": str(article_number),
                    "content_type": "text",
                }

                if len(article_text) <= chunk_size:

                    documents.append(
                        Document(
                            page_content=article_text.strip(),
                            metadata=metadata.copy()
                        )
                    )

                else:

                    chunks = self._sliding_window(
                        article_text,
                        chunk_size,
                        overlap_size
                    )

                    for chunk in chunks:
                        documents.append(
                            Document(
                                page_content=chunk.strip(),
                                metadata=metadata.copy()
                            )
                        )

        return documents


    def _sliding_window(self, text: str, chunk_size: int, overlap_size: int): 
        chunks = []
        start = 0
        n = len(text)
        while start < n:
            end = start + chunk_size
            chunks.append(text[start:end])
            new_start = end - overlap_size
            if new_start <= start:
                new_start = start + max(1, chunk_size)
            start = new_start
        return chunks

    def process_section_aware_splitter(
        self,
        text,
        metadata,
        chunk_size,
        overlap_size
    ):
        sections = self.split_by_articles(text)

        chunks = []

        for article_num, article_text in sections:

            if not article_text.strip():
                continue

            article_metadata = metadata.copy()
            article_metadata["article"] = article_num

            # Article header
            article_match = ARTICLE_PATTERN.match(article_text)


            if article_match:
                article_header = article_match.group().strip()

                article_content = article_text[
                    article_match.end():
                ].strip()

            else:
                article_header = ""

                article_content = article_text

            # Split ONLY the article if it is too large
            article_chunks = self.split_large_section(
                text=article_content,
                chunk_size=chunk_size,
                overlap_size=overlap_size
            )

            for chunk in article_chunks:

                chunk_text = (
                    f"{article_header}\n{chunk}"
                    if article_header
                    else chunk
                )

                chunks.append(
                    Document(
                        page_content=chunk_text,
                        metadata=article_metadata.copy()
                    )
                )

        return chunks


    def normalize_digits(self, text: str) -> str:

        translation = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
            "01234567890123456789"
        )

        return text.translate(translation)


    
    def split_by_articles(self, text: str):
        matches = list(ARTICLE_PATTERN.finditer(text))

        if not matches:
            return [("unknown", text)]

        sections = []

        for index, match in enumerate(matches):
            article_number = self.normalize_digits(match.group(1))

            start = match.start()
            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            )

            sections.append((article_number, text[start:end].strip()))

        return sections



    def split_large_section(
        self,
        text: str,
        chunk_size: int,
        overlap_size: int
    ):

        if len(text) <= chunk_size:
            return [text]

        words = text.split()

        chunks = []

        current_chunk = []
        current_length = 0

        for word in words:

            word_length = len(word) + 1

            if (
                current_length + word_length > chunk_size
                and current_chunk
            ):

                chunk = " ".join(current_chunk)

                chunks.append(chunk)

                overlap_words = []
                overlap_length = 0

                for previous_word in reversed(current_chunk):

                    if overlap_length + len(previous_word) + 1 > overlap_size:
                        break

                    overlap_words.insert(
                        0,
                        previous_word
                    )

                    overlap_length += len(previous_word) + 1

                current_chunk = overlap_words

                current_length = overlap_length

            current_chunk.append(word)
            current_length += word_length

        if current_chunk:
            chunks.append(
                " ".join(current_chunk)
            )

        return chunks

    async def process_pdf(
    self,
    file_id: str,
    chunk_size: int = 1000,
    overlap_size: int = 100,
):

        base_metadata = ProcessControllerEnums.BASE_METADATA.value

        file_path = os.path.join(
            self.project_path,
            file_id
        )


        pdf_loader = QalamLoader(
            file_path=file_path,
        )

        pdf_documents = pdf_loader.load()

        self.logger.info(
            f"Number of normal docs: {len(pdf_documents)}"
        )
    
         # 4. Process normal text
        documents = []

        for page in pdf_documents:

            text = self.normalize_text(
                page.page_content
            )

            if not text:
                continue

            page_documents = (
                self.process_section_aware_splitter(
                    text=text,
                    metadata={
                        **base_metadata,
                        "page": page.metadata["page"],
                    },
                    chunk_size=chunk_size,
                    overlap_size=overlap_size
                )
            )

            documents.extend(page_documents)

        # 5. Add tables

        return documents
