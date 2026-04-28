"""
Unit tests for execution/parse_resume_data.py

Tests text extraction and structured data parsing from resume bytes.
"""

import zipfile
from pathlib import Path

import pytest

from execution.parse_resume_data import extract_text_from_bytes, parse_resume_data


FIXTURE_TXT = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha" / "resume.txt"


# ---------------------------------------------------------------------------
# extract_text_from_bytes
# ---------------------------------------------------------------------------


def test_extract_text_from_txt():
    content = FIXTURE_TXT.read_bytes()
    text = extract_text_from_bytes(content, "resume.txt")
    assert "ANUSHA KAYAM" in text
    assert len(text) > 100


def test_extract_text_from_md():
    content = b"# Jane Doe\n\n## Skills\n- Python\n- SQL\n"
    text = extract_text_from_bytes(content, "resume.md")
    assert "Jane Doe" in text
    assert "Python" in text


def test_extract_text_strips_null_bytes():
    content = b"Python\x00developer\x00"
    text = extract_text_from_bytes(content, "resume.txt")
    assert "\x00" not in text
    assert "Python" in text


def test_extract_text_from_docx(tmp_path):
    docx_path = tmp_path / "resume.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Jane Doe</w:t></w:r></w:p>
    <w:p><w:r><w:t>Python developer with AWS and Docker skills</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(docx_path, "w") as z:
        z.writestr("word/document.xml", document_xml)

    content = docx_path.read_bytes()
    text = extract_text_from_bytes(content, "resume.docx")
    assert "Jane Doe" in text
    assert "Python" in text


def test_extract_text_from_unknown_extension_falls_back_to_decode():
    content = b"plain text resume"
    text = extract_text_from_bytes(content, "resume.pages")
    assert "plain text resume" in text


def test_extract_text_corrupt_docx_returns_empty():
    text = extract_text_from_bytes(b"not a real docx", "resume.docx")
    assert isinstance(text, str)
    assert text == ""


# ---------------------------------------------------------------------------
# parse_resume_data
# ---------------------------------------------------------------------------


def test_parse_resume_data_returns_all_keys():
    content = FIXTURE_TXT.read_bytes()
    result = parse_resume_data(content, "resume.txt")
    assert set(result.keys()) == {"name", "email", "skills", "experience_years", "resume_text"}


def test_parse_resume_data_extracts_name():
    content = FIXTURE_TXT.read_bytes()
    result = parse_resume_data(content, "resume.txt")
    assert result["name"] == "ANUSHA KAYAM"


def test_parse_resume_data_extracts_email():
    content = FIXTURE_TXT.read_bytes()
    result = parse_resume_data(content, "resume.txt")
    assert result["email"] == "anusha@example.com"


def test_parse_resume_data_extracts_skills():
    content = FIXTURE_TXT.read_bytes()
    result = parse_resume_data(content, "resume.txt")
    skills = result["skills"]
    assert isinstance(skills, list)
    assert len(skills) > 0
    skills_lower = [s.lower() for s in skills]
    assert any("sql" in s for s in skills_lower)


def test_parse_resume_data_experience_years_is_int():
    content = FIXTURE_TXT.read_bytes()
    result = parse_resume_data(content, "resume.txt")
    assert isinstance(result["experience_years"], int)


def test_parse_resume_data_resume_text_populated():
    content = FIXTURE_TXT.read_bytes()
    result = parse_resume_data(content, "resume.txt")
    assert len(result["resume_text"]) > 100


def test_parse_resume_data_empty_content():
    result = parse_resume_data(b"", "resume.txt")
    assert result["name"] is None
    assert result["email"] is None
    assert result["skills"] == []
    assert result["experience_years"] == 0
    assert result["resume_text"] == ""


def test_parse_resume_data_whitespace_only():
    result = parse_resume_data(b"   \n\n   ", "resume.txt")
    assert result["skills"] == []
    assert result["name"] is None


def test_parse_resume_data_skills_are_list_of_strings():
    content = FIXTURE_TXT.read_bytes()
    result = parse_resume_data(content, "resume.txt")
    for skill in result["skills"]:
        assert isinstance(skill, str)
        assert len(skill) > 0
