from anthropic import Anthropic
from dotenv import load_dotenv
import os
import json

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def ai_job_match(resume, job):
    prompt = f"""
    You are an expert recruitment AI.

    Analyze how well this resume matches the job.

    Return ONLY valid JSON:
    {{
      "match_score": number between 0 and 100,
      "reasoning": "short explanation"
    }}

    Resume:
    {json.dumps(resume, indent=2)}

    Job:
    {json.dumps(job, indent=2)}
    """

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text.strip())
