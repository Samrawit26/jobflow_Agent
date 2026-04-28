"""
Resume data extraction script.

Accepts raw file bytes + filename, extracts structured candidate data.

One responsibility: convert raw resume bytes → structured dict.

Importable and testable. No orchestration logic. No prompts.
"""

import io

from jobflow.resume.parser import structure_resume_text


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    """
    Extract plain text from resume file bytes.

    Supports:
        .pdf  → pdfplumber
        .docx → python-docx
        .txt / .md → UTF-8 decode

    Returns empty string on failure; never raises.
    """
    name_lower = (filename or "").lower()

    if name_lower.endswith(".pdf"):
        return _extract_pdf(content)
    elif name_lower.endswith(".docx"):
        return _extract_docx(content)
    else:
        text = content.decode("utf-8", errors="ignore")
        return text.replace("\x00", "")


def _extract_pdf(content: bytes) -> str:
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception:
        return ""


def _extract_docx(content: bytes) -> str:
    """Extract text from .docx bytes using stdlib zipfile + XML (no external deps)."""
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            xml_bytes = z.read("word/document.xml")
        root = ET.fromstring(xml_bytes)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for para in root.findall(".//w:p", ns):
            texts = [t.text for t in para.findall(".//w:t", ns) if t.text]
            if texts:
                paragraphs.append("".join(texts))
        return "\n".join(paragraphs)
    except Exception:
        return ""


def parse_resume_data(content: bytes, filename: str) -> dict:
    """
    Parse resume bytes into structured candidate data.

    Args:
        content:  Raw file bytes from upload.
        filename: Original filename (used to detect format).

    Returns:
        dict with keys matching the Candidate model:
            name            (str | None)
            email           (str | None)
            skills          (list[str])
            experience_years (int)
            resume_text     (str)
    """
    text = extract_text_from_bytes(content, filename)

    if not text.strip():
        return {
            "name": None,
            "email": None,
            "skills": [],
            "experience_years": 0,
            "resume_text": "",
        }

    structured = structure_resume_text(text)

    return {
        "name": structured.get("name") or None,
        "email": structured.get("email") or None,
        "skills": structured.get("skills") or [],
        "experience_years": int(structured.get("years_experience") or 0),
        "resume_text": text,
    }
