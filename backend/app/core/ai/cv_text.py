"""Extrakcia čistého textu zo životopisu (PDF alebo DOCX).

Text posielame modelu namiesto samotného súboru: je to lacnejšie a funguje
aj pre DOCX. Skenované PDF bez textovej vrstvy vrátia prázdny text; v tom
prípade sa uchádzač hodnotí len z chatu a zdôvodnenie to uvedie.
"""

from __future__ import annotations

import io
import logging
import re

from app.core.limits import MAX_CV_CHARS, MAX_CV_DOCX_BLOCKS, MAX_CV_PDF_PAGES

logger = logging.getLogger(__name__)

MAX_CHARS = MAX_CV_CHARS
MAX_PAGES = MAX_CV_PDF_PAGES
TRUNCATED_MARKER = "\n[… text životopisu bol skrátený …]"
SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


class UnsupportedCvFormat(ValueError):
    pass


def extract_text(data: bytes, filename: str) -> str:
    """Vráť text zo súboru podľa prípony. Prázdny reťazec, ak sa text nepodarilo získať."""
    ext = _extension(filename)
    if ext == ".pdf":
        text = _from_pdf(data)
    elif ext == ".docx":
        text = _from_docx(data)
    else:
        raise UnsupportedCvFormat(f"Nepodporovaný formát životopisu: {filename}")
    return _normalize(text)


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:  # noqa: BLE001
                logger.warning("CV PDF je zašifrované, text sa nedá prečítať")
                return ""
    except Exception:  # noqa: BLE001
        logger.warning("CV PDF sa nepodarilo otvoriť", exc_info=True)
        return ""

    # Čítame najviac MAX_PAGES strán a najviac MAX_CHARS znakov. 10 MB PDF môže
    # mať tisíce strán; bez stropu by samotná extrakcia textu zožrala CPU ešte
    # pred akýmkoľvek volaním modelu.
    pages: list[str] = []
    total = 0
    for index, page in enumerate(reader.pages):
        if index >= MAX_PAGES:
            logger.info("CV PDF má viac ako %d strán, zvyšok sa ignoruje", MAX_PAGES)
            break
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            logger.warning("Strana %d CV PDF sa nedala prečítať", index + 1, exc_info=True)
            continue
        pages.append(text)
        total += len(text)
        if total > MAX_CHARS:
            break
    return "\n\n".join(pages)


def _from_docx(data: bytes) -> str:
    from docx import Document

    try:
        document = Document(io.BytesIO(data))
    except Exception:  # noqa: BLE001
        logger.warning("CV DOCX sa nepodarilo otvoriť", exc_info=True)
        return ""

    # Rovnaký dôvod ako pri PDF: počet odstavcov aj znakov je ohraničený, aby
    # vygenerovaný DOCX s miliónom riadkov nezamestnal worker.
    lines: list[str] = []
    total = 0

    def add(text: str) -> bool:
        """Pridaj riadok. False = narazili sme na strop a máme skončiť."""
        nonlocal total
        lines.append(text)
        total += len(text)
        return len(lines) < MAX_CV_DOCX_BLOCKS and total <= MAX_CHARS

    for paragraph in document.paragraphs:
        if not add(paragraph.text):
            return "\n".join(lines)

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if not add(" | ".join(c for c in cells if c)):
                return "\n".join(lines)

    return "\n".join(lines)


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS].rstrip() + TRUNCATED_MARKER
    return text
