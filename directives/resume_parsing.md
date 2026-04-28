# Resume Parsing Pipeline

## Purpose

Extract structured candidate data from an uploaded resume file and persist it to the database.

---

## Inputs

| Field    | Type             | Description                          |
|----------|------------------|--------------------------------------|
| file     | UploadFile       | Resume file uploaded via HTTP POST   |
| filename | str              | Original filename (used for format detection) |

Supported formats: `.pdf`, `.docx`, `.txt`, `.md`

---

## Outputs

A saved `Candidate` record containing:

| Field            | Source                                      | Fallback         |
|------------------|---------------------------------------------|------------------|
| name             | First non-empty line of resume              | `"Unknown"`      |
| email            | Regex-matched email address                 | `"unknown@example.com"` |
| skills           | Section-parsed skills block                 | `[]`             |
| experience_years | Explicit "X years" or inferred from dates   | `0`              |
| resume_text      | Full extracted plain text                   | `""`             |

API response includes: `candidate_id`, `skills`, `message`.

---

## Steps

1. **Receive file** via `POST /upload-resume/`
2. **Read bytes** — `content = await file.read()`
3. **Extract text** — `execution/parse_resume_data.py → extract_text_from_bytes(content, filename)`
   - `.pdf` → pdfplumber (page-by-page)
   - `.docx` → stdlib zipfile + XML (no external dep)
   - `.txt` / `.md` / other → UTF-8 decode, strip null bytes
4. **Parse structure** — `structure_resume_text(text)` from `jobflow/resume/parser.py`
   - Extracts: name, email, phone, skills, education, work experience, years_experience
5. **Map to Candidate model** — only fields the model supports are stored
6. **Save to database** — `db.add()` / `db.commit()` / `db.refresh()`
7. **Return response** — `candidate_id` + `skills`

---

## Edge Cases

| Scenario                     | Behavior                                      |
|------------------------------|-----------------------------------------------|
| Empty file                   | Returns empty text; candidate stored with defaults |
| Corrupt PDF                  | pdfplumber raises → caught, returns `""`     |
| Corrupt DOCX                 | zipfile/XML parse fails → caught, returns `""` |
| No name found                | Stored as `"Unknown"`                         |
| No email found               | Stored as `"unknown@example.com"`             |
| No skills found              | `skills = []`                                 |
| Unknown file extension       | Falls back to UTF-8 decode                    |

---

## Safety Constraints

- Never write raw binary to `resume_text` — always decode to string first
- Never store null bytes (`\x00`) in text columns — stripped during decode
- Never call the Anthropic API inside this pipeline (AI refinement is opt-in, in `/parse-resume` only)
- Never write to production DB during tests

---

## Execution Script

**`execution/parse_resume_data.py`**

- `extract_text_from_bytes(content, filename) → str`
- `parse_resume_data(content, filename) → dict`

Deterministic. Importable. No orchestration logic. No I/O side effects beyond reading bytes.

---

## Tests

`tests/execution/test_parse_resume_data.py` — 15 unit tests covering:
- Text extraction for all supported formats
- Null byte stripping
- Corrupt file handling
- Structured field extraction (name, email, skills, experience_years)
- Empty and whitespace-only inputs

---

## Related Files

| File | Role |
|------|------|
| `execution/parse_resume_data.py` | Execution layer — text extraction + structuring |
| `jobflow/resume/parser.py` | `structure_resume_text()` — regex-based field extraction |
| `jobflow/app/api/main.py` | API layer — HTTP handling, DB save, response |
| `jobflow/app/models/candidate.py` | Candidate schema |
| `tests/execution/test_parse_resume_data.py` | Unit tests |
