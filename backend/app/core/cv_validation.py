"""Overenie, že nahraté CV je naozaj PDF alebo DOCX.

Prípona súboru je len meno — `virus.exe` premenovaný na `cv.pdf` ju má
správnu. Rozhoduje obsah (magic bytes). Súbor si potom stiahne admin, takže
by sa mu do počítača dostalo čokoľvek, čo uchádzač nahrá.
"""

import io
import zipfile

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"

# DOCX je ZIP balík s týmto súborom vo vnútri. Samotná ZIP hlavička nestačí,
# tú má aj .xlsx, .jar alebo obyčajný archív.
DOCX_MAIN_PART = "word/document.xml"


def detect_cv_type(content: bytes) -> str | None:
    """Prípona podľa obsahu: ".pdf", ".docx", alebo None pre čokoľvek iné."""
    # PDF môže mať pred hlavičkou pár bajtov smetí, čítačky to tolerujú.
    if PDF_MAGIC in content[:1024]:
        return ".pdf"

    if content.startswith(ZIP_MAGIC):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if DOCX_MAIN_PART in archive.namelist():
                    return ".docx"
        except zipfile.BadZipFile:
            return None

    return None
