import json

import pytest

from jobflow.matching import skill_gap


def test_detect_skill_gaps_basic():
    resume = {"skills": ["python", "aws"]}
    job = {"skills": ["Python", "docker"]}

    result = skill_gap.detect_skill_gaps(resume, job)

    assert set(result["missing_skills"]) == {"docker"}
    # one of two skills is present
    assert result["match_percentage"] == 50.0


def test_detect_skill_gaps_normalizes_case():
    # ensure uppercase/lowercase mismatches do not report missing skills
    resume = {"skills": ["Python", "DOCKER"]}
    job = {"skills": ["python", "docker", "aws"]}
    result = skill_gap.detect_skill_gaps(resume, job)
    assert set(result["missing_skills"]) == {"aws"}
    assert result["match_percentage"] == round((2 / 3) * 100, 2)


def test_detect_skill_gaps_empty_inputs():
    # resume has no skills, job has none
    assert skill_gap.detect_skill_gaps({}, {}) == {
        "missing_skills": [],
        "match_percentage": 0,
    }

    # resume empty but job has skills
    result = skill_gap.detect_skill_gaps({}, {"skills": ["a", "b"]})
    assert set(result["missing_skills"]) == {"a", "b"}
    assert result["match_percentage"] == 0

    # job has empty skills list (should behave same as missing)
    assert skill_gap.detect_skill_gaps({"skills": ["x"]}, {"skills": []}) == {
        "missing_skills": [],
        "match_percentage": 0,
    }


def test_generate_gap_recommendations_parses_json(monkeypatch):
    # stub out the anthropic client so we don't make a network call
    fake_text = '{"gap_summary": "hi", "improvement_steps": [], "learning_recommendations": [], "resume_advice": []}'

    class DummyContent:
        def __init__(self, text):
            self.text = text

    class DummyResponse:
        def __init__(self, text):
            self.content = [DummyContent(text)]

    def fake_create(**kwargs):
        # simply return an object with the expected shape
        return DummyResponse(fake_text)

    monkeypatch.setattr(
        skill_gap,
        "_get_client",
        lambda: type("C", (), {"messages": type("M", (), {"create": staticmethod(fake_create)})})(),
    )

    resume = {"skills": ["a"]}
    job = {"skills": ["a", "b"]}
    missing = ["b"]
    data = skill_gap.generate_gap_recommendations(resume, job, missing)

    assert data["gap_summary"] == "hi"
    assert data["improvement_steps"] == []


def test_generate_gap_recommendations_invalid_json(monkeypatch):
    # client returns something that's not JSON
    class DummyContent:
        def __init__(self, text):
            self.text = text

    class DummyResponse:
        def __init__(self, text):
            self.content = [DummyContent(text)]

    def fake_create(**kwargs):
        return DummyResponse("not json at all")

    monkeypatch.setattr(
        skill_gap,
        "_get_client",
        lambda: type("C", (), {"messages": type("M", (), {"create": staticmethod(fake_create)})})(),
    )

    with pytest.raises(ValueError):
        skill_gap.generate_gap_recommendations({"skills": []}, {"skills": []}, [])


def test_analyze_skill_gap_ai_success(monkeypatch):
    resume = {"skills": ["python"]}
    job = {"skills": ["python", "docker"]}

    fake_ai = {
        "gap_summary": "foo",
        "improvement_steps": ["step"],
        "learning_recommendations": ["learn"],
        "resume_advice": ["add experience"],
    }

    monkeypatch.setattr(
        skill_gap,
        "generate_gap_recommendations",
        lambda r, j, m: fake_ai,
    )

    result = skill_gap.analyze_skill_gap(resume, job)

    # base fields from detection
    assert set(result["missing_skills"]) == {"docker"}
    assert result["match_percentage"] == 50.0

    # AI fields propagated
    assert result["gap_summary"] == "foo"
    assert result["ai_generated"] is True


def test_analyze_skill_gap_parse_failure(monkeypatch):
    # generate_gap_recommendations raises ValueError -> ai_generated False
    resume = {"skills": []}
    job = {"skills": ["x"]}

    monkeypatch.setattr(
        skill_gap,
        "generate_gap_recommendations",
        lambda r, j, m: (_ for _ in ()).throw(ValueError("oops")),
    )

    result = skill_gap.analyze_skill_gap(resume, job)
    assert result["ai_generated"] is False


def test_analyze_skill_gap_ai_failure(monkeypatch):
    resume = {"skills": []}
    job = {"skills": ["x"]}

    def bomb(r, j, m):
        raise RuntimeError("boom")

    monkeypatch.setattr(skill_gap, "generate_gap_recommendations", bomb)

    result = skill_gap.analyze_skill_gap(resume, job)
    assert result["missing_skills"] == ["x"]
    assert result["match_percentage"] == 0
    assert result["ai_generated"] is False


# ensure that the functions import correctly and have docstrings
def test_module_exports():
    assert hasattr(skill_gap, "detect_skill_gaps")
    assert hasattr(skill_gap, "generate_gap_recommendations")
    assert hasattr(skill_gap, "analyze_skill_gap")

