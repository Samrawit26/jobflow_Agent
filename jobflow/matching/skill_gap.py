from dotenv import load_dotenv
import os
import json

# load environment early so the client is ready for any import-time use
load_dotenv()
_client = None


def _get_client():
    """Return a shared Anthropic client, creating it on first access.

    Having a helper lets us monkeypatch it easily from tests and avoids
    repeated global initialization during import.
    """
    global _client
    if _client is None:
        from anthropic import Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # mirror the behaviour in ai_service so a missing key fails early
            raise ValueError("ANTHROPIC_API_KEY not found. Check your .env file.")
        _client = Anthropic(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Detection / analysis helpers
# ---------------------------------------------------------------------------

def detect_skill_gaps(resume, job):
    """Return basic information about skills the candidate is missing.

    * ``resume`` and ``job`` are dictionaries with a ``skills`` key.
    * Skills coming from the job posting are lower-cased for comparison.
    * ``missing_skills`` is a list of job skills not present on the resume.
    * ``match_percentage`` reflects how many of the job's skills the
      resume contains (0-100, rounded to two decimal places).

    Examples
    --------
    >>> detect_skill_gaps({'skills': ['python']}, {'skills': ['Python','docker']})
    {'missing_skills': ['docker'], 'match_percentage': 50.0}
    """

    # normalize both sides to lowercase strings so comparison is case-\
    # insensitive.  resumes often mix case which previously led to false\
    # positives for missing skills.
    resume_skills = set([s.lower() for s in resume.get("skills", [])])
    job_skills = set([s.lower() for s in job.get("skills", [])])

    missing = list(job_skills - resume_skills)

    if job_skills:
        match_percentage = round(
            (len(job_skills.intersection(resume_skills)) / len(job_skills)) * 100,
            2,
        )
    else:
        match_percentage = 0

    return {"missing_skills": missing, "match_percentage": match_percentage}


# ---------------------------------------------------------------------------
# AI integration
# ---------------------------------------------------------------------------

def generate_gap_recommendations(resume, job, missing_skills):
    """Ask the Anthropics API to provide guidance on skill gaps.

    The function constructs a simple prompt containing the resume,
    the job posting, and the list of missing skills.  The API is expected
    to return a JSON document matching the schema shown below; this helper
    converts the response text into a Python dictionary.

    The prompt is intentionally narrow in order to make it easier to test
    and reason about.
    """

    prompt = f"""
    You are a senior career advisor AI.

    A candidate applied for this job.

    Job Required Skills:
    {job.get("skills", [])}

    Candidate Skills:
    {resume.get("skills", [])}

    Missing Skills:
    {missing_skills}

    Provide:

    1) Short explanation of the skill gap
    2) Practical steps to improve
    3) Suggested learning areas
    4) Resume improvement advice

    Return ONLY valid JSON:

    {{
        "gap_summary": "",
        "improvement_steps": [],
        "learning_recommendations": [],
        "resume_advice": []
    }}
    """

    client = _get_client()
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )

    # in practice the SDK returns a list; copy behaviour from ai_matcher
    text = response.content[0].text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # propagate a clear error that can be caught by callers/tests
        raise ValueError("AI response was not valid JSON: %r" % text)


def analyze_skill_gap(resume, job):
    """Combined helper that attaches AI recommendations to the basic gap data.

    The return value always contains the keys produced by
    :func:`detect_skill_gaps` with two additional fields when the AI call
    succeeds:

    * ``gap_summary``
    * ``improvement_steps``
    * ``learning_recommendations``
    * ``resume_advice``
    * ``ai_generated`` (``True`` if the AI call succeeded, ``False``
      otherwise)
    """

    gap_data = detect_skill_gaps(resume, job)

    try:
        ai_advice = generate_gap_recommendations(
            resume,
            job,
            gap_data["missing_skills"],
        )
        gap_data.update(ai_advice)
        gap_data["ai_generated"] = True
    except Exception:
        gap_data["gap_summary"] = ""
        gap_data["improvement_steps"] = []
        gap_data["learning_recommendations"] = []
        gap_data["resume_advice"] = []
        gap_data["ai_generated"] = False

    return gap_data
