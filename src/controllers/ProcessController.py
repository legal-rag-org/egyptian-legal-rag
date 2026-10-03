from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import TextLoader
from .loaders import OCRPDFLoader, PDFTableDetector, TableLoader, PDFTextLayerLoader
import re
from models import ProcessingEnum
from .enums.nlp import ProcessControllerEnums
import logging
from typing import List
import re
from dataclasses import dataclass

@dataclass
class Document:
    page_content : str
    metadata: dict

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

        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(
            self.project_path,
            file_id
        )

        if not os.path.exists(file_path):
            return None

        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        elif file_ext == ProcessingEnum.PDF.value:
            return PDFTextLayerLoader(file_path)

        return None

    def get_file_content(self, file_id: str):

        loader = self.get_file_loader(file_id=file_id)

        if loader:
         return loader.load()

        return None

    def normalize_text(self, text: str) -> str:

        lines = []

        for line in text.splitlines():

            line = line.strip()

            if len(line) > 1:
                lines.append(line)

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
        base_metadata = ProcessControllerEnums.base_metadata.value

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


    def split_by_official_gazette(self, text: str):
        pattern = re.compile(
            r"(?=الجريدة\s+الرسمية\s*[-–—]\s*"
            r"العدد\s+\d+\s+مكرر"
            r"(?:\s*\([^)]+\))?"
            r"\s+في\s+\d+\s+"
            r"(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)"
            r"\s+سنة\s+\d{4})"
        )

        matches = list(pattern.finditer(text))

        if not matches:
            return [("unknown", text)]

        sections = []

        for index, match in enumerate(matches):
            start = match.start()

            if index + 1 < len(matches):
                end = matches[index + 1].start()
            else:
                end = len(text)

            section_text = text[start:end].strip()

            if section_text:
                sections.append(
                    (
                        match.group().strip(),
                        section_text
                    )
                )

        return sections


    def _chunk_gazette_section(
    self,
    section_title: str,
    section_text: str,
    chunk_size: int,
):
        # Remove the title from the section body
        body = section_text[len(section_title):].strip()

        # Reserve space for the title
        available_size = chunk_size - len(section_title) - 1

        if available_size <= 0:
            raise ValueError(
                "chunk_size is too small for the gazette header."
            )

        chunks = []

        start = 0
        while start < len(body):
            body_chunk = body[start:start + available_size]

            chunk = f"{section_title}\n{body_chunk}"

            chunks.append(chunk)

            start += available_size

        return chunks



    def process_structured_splitter(
    self,
    text: str,
    metadata: dict,
    chunk_size: int = 1000,
    overlap_size: int = 100
):
        documents = []

        record_pattern = re.compile(r'(?=(?:السجل|الرمز):\s*\S+)')
        blocks = [b.strip() for b in record_pattern.split(text) if b.strip()]

        for block in blocks:
            is_pure_table = re.search(r'\|.*\|', block) and '---' in block and not block.startswith(('السجل:', 'الرمز:'))

            if is_pure_table:
                for chunk_text in self._chunk_table_block(block, chunk_size):
                    documents.append(Document(page_content=chunk_text.strip(), metadata=metadata.copy()))

            elif block.startswith(('السجل:', 'الرمز:')):
                if len(block) <= chunk_size:
                    documents.append(Document(page_content=block, metadata=metadata.copy()))
                else:
                    for chunk_text in self._chunk_by_heading(block, chunk_size, overlap_size):
                        documents.append(Document(page_content=chunk_text.strip(), metadata=metadata.copy()))
            else:
                for chunk_text in self._chunk_by_heading(block, chunk_size, overlap_size):
                    documents.append(Document(page_content=chunk_text.strip(), metadata=metadata.copy()))

        return documents


    def _chunk_table_block(self, block: str, chunk_size: int):
        lines = block.split('\n')
        header_lines = []
        row_lines = []
        seen_separator = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            is_separator = bool(re.match(r'^\|?[\s\-:|]+\|?$', stripped)) and '-' in stripped
            if is_separator:
                header_lines.append(line)
                seen_separator = True
            elif seen_separator and stripped.startswith('|'):
                row_lines.append(line)
            else:
                header_lines.append(line)

        header = '\n'.join(header_lines)
        chunks = []
        current = header

        for row in row_lines:
            if len(current) + len(row) > chunk_size:
                chunks.append(current)
                current = header + '\n' + row
            else:
                current += '\n' + row

        if current.strip() != header.strip():
            chunks.append(current)

        return chunks if chunks else [block]


    def _chunk_by_heading(self, block: str, chunk_size: int, overlap_size: int):
        heading_pattern = re.compile(
            r'(?=(?:الباب|الفصل|القسم|العنوان)[^\n]*:)|(?=^#{1,3}\s)',
            re.MULTILINE
        )
        sub_blocks = [sb.strip() for sb in heading_pattern.split(block) if sb.strip()]

        result = []
        for sb in sub_blocks:
            if re.search(r'\|.*\|', sb) and '---' in sb:
                result.extend(self._chunk_table_block(sb, chunk_size))
            elif len(sb) <= chunk_size:
                result.append(sb)
            else:
                result.extend(self._sliding_window(sb, chunk_size, overlap_size))
        return result


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
            article_match = re.match(
                r"(?:مادة|ﻣﺎﺩﺓ)"
                r"\s*\("
                r"\s*[0-9٠-٩۰-۹]+\s*"
                r"\)"
                r"\s*:?",
                article_text
            )

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

        pattern = (
            r"(?:مادة|ﻣﺎﺩﺓ)"
            r"\s*"
            r"\("
            r"\s*"
            r"([0-9٠-٩۰-۹]+)"
            r"\s*"
            r"\)"
            r"\s*:"
        )

        matches = list(
            re.finditer(
                pattern,
                text,
                flags=re.IGNORECASE
            )
        )

        if not matches:
            return [("unknown", text)]

        sections = []

        for index, match in enumerate(matches):

            article_number = self.normalize_digits(
                match.group(1)
            )

            start = match.start()

            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            )

            article_text = text[
                start:end
            ].strip()

            sections.append(
                (
                    article_number,
                    article_text
                )
            )

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

        base_metadata = {
            "domain": "insurance",
            "source": "قانون العمل الجديد رقم 148 لسنة 2019",
            "document_type": "law",
            "law_number": "148",
            "law_year": "2019",
            "language": "ar",
            "file_url": "https://www.nosi.gov.eg/ar/Lists/NOSILibrary/2-12-2019%20%D9%83%D8%AA%D8%A7%D8%A8%20%D8%A7%D9%84%D9%82%D8%A7%D9%86%D9%88%D9%86%20%D8%A7%D9%84%D8%AC%D8%AF%D9%8A%D8%AF.pdf",
        }

        file_path = os.path.join(
            self.project_path,
            file_id
        )

        table_detector = PDFTableDetector(
            file_path=file_path
        )

        table_pages = table_detector.detect_table_pages()

        self.logger.info(
            f"Detected table pages: {table_pages}"
        )

        ocrloader = OCRPDFLoader(
            file_path=file_path,
            excluded_pages=table_pages,
        )

        normal_documents = ocrloader.load()

        self.logger.info(
            f"Number of normal docs: {len(normal_documents)}"
        )

        table_loader = TableLoader(
            file_path=file_path,
            dpi=150
        )

        table_documents = []

        # # Process each table page individually
        # for page_number in table_pages:

        #      image_path = None

        #      try:

        #          self.logger.info(
        #              f"Starting vision page: {page_number}"
        #          )

        #          image_path = table_loader.render_page(
        #              page_number=page_number
        #          )

        #          self.logger.info(
        #              f"Rendered page: {page_number}"
        #          )

        #          texts = await self.vision_model.extract(
        #              images=[image_path]
        #          )

        #          text = texts[0] if texts else ""

        #          self.logger.info(
        #              f"Vision extraction finished for page: {page_number}"
        #          )

        #          if not text.strip():
        #              continue

        #          table_documents.append(
        #            Document(
        #                  page_content=text,
        #                  metadata={
        #                      **base_metadata,
        #                      "page": page_number,
        #                      "content_type": "table",
        #                  },
        #              )
        #          )

        #      except Exception as e:

        #          self.logger.error(
        #              f"Error processing page {page_number}: {e}",
        #              exc_info=True,
        #          )

        #      finally:

        #          if image_path and os.path.exists(image_path):
        #              os.unlink(image_path)

        # 4. Process normal text
        documents = []

        for page in normal_documents:

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
        documents.extend(table_documents)

        return documents
