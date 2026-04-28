"""
Unit tests for execution/match_resume_to_job.py
"""

import pytest

from execution.match_resume_to_job import match_resume_to_job


def test_exact_match_example_from_spec():
    candidate = ["python", "sql", "power bi"]
    job = ["python", "sql", "aws"]
    result = match_resume_to_job(candidate, job)
    assert result["score"] == 67
    assert result["matched_skills"] == ["python", "sql"]
    assert result["missing_skills"] == ["aws"]


def test_perfect_match():
    candidate = ["python", "sql", "aws"]
    job = ["python", "sql", "aws"]
    result = match_resume_to_job(candidate, job)
    assert result["score"] == 100
    assert result["missing_skills"] == []


def test_zero_match():
    candidate = ["java", "spring"]
    job = ["python", "sql", "aws"]
    result = match_resume_to_job(candidate, job)
    assert result["score"] == 0
    assert result["matched_skills"] == []
    assert set(result["missing_skills"]) == {"python", "sql", "aws"}


def test_empty_job_skills():
    result = match_resume_to_job(["python", "sql"], [])
    assert result["score"] == 0
    assert result["matched_skills"] == []
    assert result["missing_skills"] == []


def test_empty_candidate_skills():
    result = match_resume_to_job([], ["python", "sql"])
    assert result["score"] == 0
    assert result["matched_skills"] == []
    assert result["missing_skills"] == ["python", "sql"]


def test_both_empty():
    result = match_resume_to_job([], [])
    assert result["score"] == 0


def test_case_insensitive_matching():
    candidate = ["Python", "SQL", "Power BI"]
    job = ["python", "sql", "power bi"]
    result = match_resume_to_job(candidate, job)
    assert result["score"] == 100


def test_whitespace_normalization():
    candidate = ["power  bi", "node.js"]
    job = ["power bi", "node.js"]
    result = match_resume_to_job(candidate, job)
    assert result["score"] == 100


def test_partial_candidate_match():
    candidate = ["python", "docker"]
    job = ["python", "sql", "aws", "docker"]
    result = match_resume_to_job(candidate, job)
    assert result["score"] == 50
    assert set(result["matched_skills"]) == {"python", "docker"}
    assert set(result["missing_skills"]) == {"sql", "aws"}


def test_return_keys_present():
    result = match_resume_to_job(["python"], ["python", "sql"])
    assert "score" in result
    assert "matched_skills" in result
    assert "missing_skills" in result


def test_score_is_integer():
    result = match_resume_to_job(["python"], ["python", "sql", "aws"])
    assert isinstance(result["score"], int)


def test_score_rounds_correctly():
    # 1 of 3 = 33.33... → rounds to 33
    result = match_resume_to_job(["python"], ["python", "sql", "aws"])
    assert result["score"] == 33


def test_candidate_superset_of_job():
    candidate = ["python", "sql", "aws", "docker", "kubernetes"]
    job = ["python", "sql"]
    result = match_resume_to_job(candidate, job)
    assert result["score"] == 100
    assert result["missing_skills"] == []


def test_matched_and_missing_cover_all_job_skills():
    candidate = ["python"]
    job = ["python", "sql", "aws"]
    result = match_resume_to_job(candidate, job)
    all_accounted = set(result["matched_skills"]) | set(result["missing_skills"])
    assert all_accounted == set(job)
