import pdfplumber
import docx
import os


def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    return text


def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])


def extract_text_from_txt(file_path):
    with open(file_path, "r", errors="ignore") as f:
        return f.read()


def parse_resume(file_path):

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)

    elif ext == ".docx":
        return extract_text_from_docx(file_path)

    elif ext == ".txt":
        return extract_text_from_txt(file_path)

    else:
        raise ValueError(f"Unsupported file type: {ext}")
