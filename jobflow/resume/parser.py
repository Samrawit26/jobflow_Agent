# AI refinement imports and function
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import json

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def refine_resume_with_ai(raw_text, structured_data):
  prompt = f"""
  You are a senior ATS resume intelligence engine.

  Improve and correct the structured resume below.

  - Fix missing or incorrect fields
  - Improve skills extraction
  - Normalize job titles
  - Remove duplicates
  - Ensure realistic years_experience
  - Ensure valid JSON output

  Return ONLY valid JSON.

  Raw Resume:
  ----------------
  {raw_text}
  ----------------

  Current Parsed Data:
  ----------------
  {json.dumps(structured_data, indent=2)}
  ----------------
  """

  response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1200,
    messages=[{"role": "user", "content": prompt}]
  )

  return json.loads(response.content[0].text.strip())
import pdfplumber
from docx import Document
import re


def extract_text_from_pdf(file_path):
  text = ""
  with pdfplumber.open(file_path) as pdf:
    for page in pdf.pages:
      text += page.extract_text() or ""
  return text


def extract_text_from_docx(file_path):
  doc = Document(file_path)
  return "\n".join([para.text for para in doc.paragraphs])


def extract_resume_text(file_path):
  if file_path.endswith(".pdf"):
    return extract_text_from_pdf(file_path)
  elif file_path.endswith(".docx"):
    return extract_text_from_docx(file_path)
  else:
    raise ValueError("Unsupported file format. Use PDF or DOCX.")


def _find_email(text):
  m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
  return m.group(0) if m else None


def _find_phone(text):
  m = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", text)
  if not m:
    return None
  digits = re.sub(r"\D", "", m.group(0))
  if len(digits) == 10:
    return f"+1-{digits[0:3]}-{digits[3:6]}-{digits[6:]}"
  elif len(digits) > 10:
    return f"+{digits[0]}-{digits[1:4]}-{digits[4:7]}-{digits[7:11]}"
  return m.group(0)


def _extract_section_block(text, header_names):
  # Find header line (case-insensitive), then take following lines until a blank line
  pattern = re.compile(r"(?im)^(?:" + "|".join(re.escape(h) for h in header_names) + r")\s*[:\-]?\s*$", re.MULTILINE)
  m = pattern.search(text)
  if not m:
    return ""
  start = m.end()
  rest = text[start:]
  # stop at two consecutive newlines or next all-caps header
  m2 = re.search(r"\n\s*\n", rest)
  block = rest[:m2.start()] if m2 else rest
  return block.strip()


def _normalize_skill(skill):
  return skill.strip().lower()

def _parse_skills(text):
  block = _extract_section_block(text, ["Skills", "Technical Skills", "Skills & Technologies"])
  if not block:
    m = re.search(r"(?i)skills?\s*[:\-]\s*(.+)", text)
    if m:
      block = m.group(1)
  if not block:
    return []
  parts = re.split(r"[,\n•\-;]+", block)
  cleaned = []
  for p in parts:
    skill = _normalize_skill(p)
    if skill and len(skill) > 1:
      cleaned.append(skill)
  unique_skills = list(dict.fromkeys(cleaned))
  return unique_skills


def _parse_education(text):
  block = _extract_section_block(text, ["Education", "Academic Background"]) or text
  lines = [l.strip() for l in block.splitlines() if l.strip()]
  educations = []
  for line in lines:
    year_m = re.search(r"(19|20)\d{2}", line)
    year = year_m.group(0) if year_m else ""
    parts = [p.strip() for p in re.split(r",| at | - ", line) if p.strip()]
    degree = parts[0] if parts else ""
    institution = parts[1] if len(parts) > 1 else ""
    degree = degree.lower()
    degree = degree.replace("bachelor of science", "bsc")
    degree = degree.replace("master of science", "msc")
    educations.append({"degree": degree, "institution": institution, "year": year})
    if len(educations) >= 5:
      break
  return educations


def _parse_work_experience(text):
  block = _extract_section_block(text, ["Experience", "Work Experience", "Employment History"]) or text
  raw_items = re.split(r"\n\s*\n|\n[-•]\s*", block)
  items = []
  for raw in raw_items:
    line = raw.strip()
    if not line:
      continue
    title = ""
    company = ""
    duration = ""
    responsibilities = []
    rlines = [l.strip() for l in line.splitlines() if l.strip()]
    if not rlines:
      continue
    header = rlines[0]
    dur_m = re.search(r"(\b(?:19|20)\d{2}\b).*?(?:\b(?:19|20)\d{2}\b)?|Present|present", header)
    if dur_m:
      duration = dur_m.group(0)
    if " at " in header:
      tparts = header.split(" at ", 1)
      title = tparts[0].strip()
      rest = tparts[1]
      comp = re.split(r"[–—\-]\s*|,\s*", rest)[0]
      company = comp.strip()
    else:
      parts = re.split(r"[–—\-@,]\s*", header)
      if len(parts) >= 2:
        title = parts[0].strip()
        company = parts[1].strip()
      else:
        title = header
    if len(rlines) > 1:
      for rr in rlines[1:]:
        for part in re.split(r"\n\s*[-•]\s*|;|\n", rr):
          p = part.strip()
          if p:
            responsibilities.append(p)
    items.append({
      "title": title or None,
      "company": company or None,
      "duration": duration or None,
      "responsibilities": responsibilities,
    })
    if len(items) >= 10:
      break
  # Deduplicate by (title, company)
  seen = set()
  unique_items = []
  for item in items:
    key = (item["title"], item["company"])
    if key not in seen:
      seen.add(key)
      unique_items.append(item)
  return unique_items


def _estimate_years_experience(text):
  # first look for explicit "X years"
  m = re.search(r"(\d+)\+?\s+years?", text, re.I)
  if m:
    try:
      return int(m.group(1))
    except Exception:
      pass
  # otherwise infer from years mentioned in experience dates
  years = [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", text)]
  if years:
    try:
      return max(years) - min(years)
    except Exception:
      pass
  return 0
def _guess_name(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[0] if lines else ""

def structure_resume_text(text):
    email = _find_email(text) or None
    phone = _find_phone(text) or None
    name = _guess_name(text) or None
    skills = _parse_skills(text)
    education = _parse_education(text)
    work_experience = _parse_work_experience(text)
    years_experience = _estimate_years_experience(text)
    summary_block = _extract_section_block(text, ["Summary", "Professional Summary", "Profile"]) or ""
    if not summary_block:
        m = re.split(r"\n\s*\n", text)
        summary_block = m[0].strip() if m else ""
    structured = {
        "name": name.strip() if name else None,
        "email": email.lower() if email else None,
        "phone": phone,
        "skills": skills,
        "years_experience": int(years_experience) if years_experience else 0,
        "education": education,
        "work_experience": work_experience,
        "summary": summary_block.strip() if summary_block else None,
    }
    return structured

# Confidence function

def calculate_confidence(structured):
    score = 0
    total = 6  # total criteria

    if structured.get("name"):
        score += 1
    if structured.get("email"):
        score += 1
    if structured.get("phone"):
        score += 1
    if structured.get("skills"):
        score += 1
    if structured.get("work_experience"):
        score += 1
    if structured.get("education"):
        score += 1

    return round(score / total, 2)

def parse_resume(file_path, confidence_threshold=0.7):
  text = extract_resume_text(file_path)
  structured_data = structure_resume_text(text)

  confidence = calculate_confidence(structured_data)
  structured_data["confidence_score"] = confidence

  if confidence < confidence_threshold:
    try:
      refined_data = refine_resume_with_ai(text, structured_data)
      refined_data["confidence_score"] = confidence
      refined_data["refined_by_ai"] = True
      return refined_data
    except Exception:
      structured_data["refined_by_ai"] = False
      return structured_data

  structured_data["refined_by_ai"] = False
  return structured_data