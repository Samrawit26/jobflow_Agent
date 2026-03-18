import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found. Check your .env file.")

client = Anthropic(api_key=api_key)


def analyze_job_match(candidate, job):
    prompt = f"""
    You are an expert recruiter AI.

    Candidate:
    {candidate}

    Job:
    {job}

    Analyze:
    1. Match score from 0-100
    2. Strengths
    3. Gaps
    4. Final recommendation

    Return JSON only.
    """

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    import json
    return json.loads(response.content[0].text)
    