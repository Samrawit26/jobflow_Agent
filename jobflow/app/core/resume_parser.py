"""
Resume parser with stdlib-only text extraction.

Extracts text and skills from resume files (.txt, .md, .docx).
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# Canonical skill names — these are the values returned by extract_skills_from_text().
# Rules: min 3 chars (see _SHORT_WHITELIST for exceptions), no formatting variants
# (e.g. "powerbi" is NOT here — it lives in SKILL_SYNONYMS and maps to "power bi").
SKILL_KEYWORDS: set[str] = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "rust",
    "scala", "kotlin", "swift", "php", "golang",
    # Databases
    "sql", "nosql", "postgresql", "mysql", "mongodb", "redis", "cassandra",
    "sqlite", "oracle", "dynamodb",
    # Cloud & infra
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    # BI & visualisation
    "power bi", "tableau", "looker", "qlik", "excel", "vba",
    "power query", "ssrs", "ssis", "ssas", "dax", "mdx",
    # Data engineering
    "spark", "hadoop", "kafka", "airflow", "dbt", "snowflake", "redshift",
    "bigquery", "etl", "elt", "data warehouse", "data lake", "data pipeline",
    # Frameworks & libraries
    "fastapi", "django", "flask", "spring", "react", "angular", "vue",
    "node.js", "bootstrap", "tailwind", "sass",
    # ML / AI
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "machine learning", "deep learning", "nlp", "computer vision",
    # DevOps & tooling
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "graphql", "microservices", "rest api", "api", "devops", "linux", "unix",
    "bash", "powershell", "ci/cd",
    # Methodologies
    "agile", "scrum", "kanban", "sdlc", "tdd", "bdd",
    # Domains
    "data science", "business intelligence",
}

# 2-char terms that are unambiguous technical skills (exempt from the 3-char minimum).
_SHORT_WHITELIST: set[str] = {"go", "r"}  # Go lang, R lang

# Aliases and formatting variants that map to a canonical SKILL_KEYWORDS entry.
# When an alias is found in text the canonical skill is added to results.
# Keeps output normalized: "PowerBI" and "power-bi" both resolve to "power bi".
SKILL_SYNONYMS: dict[str, list[str]] = {
    "power bi":          ["powerbi", "power-bi"],
    "node.js":           ["nodejs", "node js"],
    "sql":               ["structured query language", "t-sql", "tsql", "pl/sql", "plsql"],
    "kubernetes":        ["k8s"],
    "javascript":        ["js"],
    "ci/cd":             ["continuous integration", "continuous deployment",
                          "continuous delivery", "continuous integration/continuous deployment"],
    "etl":               ["extract transform load", "extract, transform, load"],
    "machine learning":  ["predictive modeling", "predictive modelling", "ml algorithms"],
    "python":            ["python3", "python 3"],
    "tableau":           ["tableau desktop", "tableau server"],
    "rest api":          ["restful api", "rest apis", "restful apis"],
}

# Precomputed reverse lookup: alias (lowercased) → canonical skill.
_SYNONYM_LOOKUP: dict[str, str] = {
    alias.lower(): canonical
    for canonical, aliases in SKILL_SYNONYMS.items()
    for alias in aliases
}

# Context phrases that imply specific skills when the skill wasn't matched directly.
# Each key is a phrase that strongly signals a particular tool domain.
# Conservative: phrases are specific enough to avoid false positives
# (e.g. "data visualization" alone is NOT here because it's used for matplotlib/D3 too).
CONTEXT_INFERENCE: dict[str, list[str]] = {
    "power bi dashboard":       ["power bi"],
    "power bi report":          ["power bi"],
    "tableau dashboard":        ["tableau"],
    "tableau workbook":         ["tableau"],
    "ssrs report":              ["ssrs"],
    "bi reporting":             ["power bi", "ssrs"],
    "business intelligence reporting": ["power bi", "ssrs"],
    "data visualization tools": ["power bi", "tableau"],
}


def extract_text_from_resume(path: str) -> str:
    """
    Extract text from resume file.

    Supports .txt, .md, .docx formats. .doc is NOT supported.

    Args:
        path: Path to resume file

    Returns:
        Extracted text as string

    Raises:
        ValueError: If file format is .doc or unsupported
        FileNotFoundError: If file doesn't exist
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    suffix = path_obj.suffix.lower()

    # .doc is explicitly not supported
    if suffix == ".doc":
        raise ValueError(
            "Legacy .doc format is not supported. "
            "Please convert to .docx or .txt format."
        )

    # Handle .txt and .md
    if suffix in {".txt", ".md"}:
        return _read_text_file(path)

    # Handle .docx
    if suffix == ".docx":
        return _extract_text_from_docx(path)

    # Unsupported format
    raise ValueError(
        f"Unsupported resume format: {suffix}. "
        f"Supported formats: .txt, .md, .docx"
    )


def _read_text_file(path: str) -> str:
    """Read text file with UTF-8 encoding, ignoring errors."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _extract_text_from_docx(path: str) -> str:
    """
    Extract text from .docx file using stdlib only.

    .docx is a ZIP archive containing XML files. This extracts text
    from word/document.xml.

    Args:
        path: Path to .docx file

    Returns:
        Extracted text with paragraphs separated by newlines
    """
    try:
        with zipfile.ZipFile(path, "r") as docx_zip:
            # Read the main document XML
            try:
                xml_content = docx_zip.read("word/document.xml")
            except KeyError:
                # Some docx files might have different structure
                return ""

            # Parse XML
            root = ET.fromstring(xml_content)

            # Define namespace
            namespaces = {
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            }

            # Extract text from all text nodes
            paragraphs = []
            for paragraph in root.findall(".//w:p", namespaces):
                texts = []
                for text_node in paragraph.findall(".//w:t", namespaces):
                    if text_node.text:
                        texts.append(text_node.text)
                if texts:
                    paragraphs.append("".join(texts))

            return "\n".join(paragraphs)

    except zipfile.BadZipFile:
        raise ValueError(f"Invalid .docx file: {path}")
    except ET.ParseError:
        raise ValueError(f"Cannot parse .docx XML: {path}")


def _normalize_text(text: str) -> str:
    """Lowercase and collapse all whitespace to a single space."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_skills_from_text(text: str) -> list[str]:
    """
    Extract skills from resume text using three-step intelligent matching.

    Step 1 — Keyword match:
        Whole-word (word-boundary) scan against SKILL_KEYWORDS and _SHORT_WHITELIST.
        Returns only canonical skill names.

    Step 2 — Synonym match:
        Scans SKILL_SYNONYMS aliases. If an alias is found and the canonical
        skill is not yet in results, adds the canonical form.
        Example: "PowerBI" → adds "power bi".

    Step 3 — Context inference:
        Matches CONTEXT_INFERENCE phrases. Only specific multi-word phrases
        trigger inference to prevent false positives.
        Example: "power bi dashboard" → adds "power bi" if not already found.

    All matching is case-insensitive with normalised whitespace.
    No acronym or CamelCase scanning (those produce noise — names, locations).

    Args:
        text: Resume or job description text.

    Returns:
        List of canonical skill strings (lowercase, deduplicated, stable order).
    """
    if not text:
        return []

    normalized = _normalize_text(text)
    found_skills: list[str] = []
    seen: set[str] = set()

    def _add(skill: str) -> None:
        if skill not in seen:
            found_skills.append(skill)
            seen.add(skill)

    # ── Step 1: curated keyword scan ────────────────────────────────────────
    all_keywords = SKILL_KEYWORDS | _SHORT_WHITELIST
    for skill in sorted(all_keywords):
        if len(skill) < 3 and skill not in _SHORT_WHITELIST:
            continue
        if re.search(rf"\b{re.escape(skill)}\b", normalized):
            _add(skill)

    # ── Step 2: synonym / alias scan ────────────────────────────────────────
    for alias, canonical in sorted(_SYNONYM_LOOKUP.items()):
        if canonical not in seen:
            if re.search(rf"\b{re.escape(alias)}\b", normalized):
                _add(canonical)

    # ── Step 3: context inference ────────────────────────────────────────────
    for phrase, inferred in CONTEXT_INFERENCE.items():
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            for skill in inferred:
                _add(skill)

    return found_skills
