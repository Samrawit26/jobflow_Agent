"""
Unit tests for execution/rank_candidates.py
"""

import pytest

from execution.rank_candidates import rankCandidates


JOB_SKILLS = {
    "required": ["python", "sql"],
    "optional": ["aws"],
}

CANDIDATES = [
    {"name": "Alice",   "skills": ["python", "sql"]},
    {"name": "Bob",     "skills": ["python"]},
    {"name": "Charlie", "skills": ["python", "sql", "aws"]},
]


def test_spec_example_scores():
    ranked = rankCandidates(CANDIDATES, JOB_SKILLS)
    scores = {r["name"]: r["score"] for r in ranked}
    assert scores["Charlie"] == 100
    assert scores["Alice"] == 70
    assert scores["Bob"] == 35


def test_sorted_highest_first():
    ranked = rankCandidates(CANDIDATES, JOB_SKILLS)
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_charlie_is_first():
    ranked = rankCandidates(CANDIDATES, JOB_SKILLS)
    assert ranked[0]["name"] == "Charlie"


def test_bob_is_last():
    ranked = rankCandidates(CANDIDATES, JOB_SKILLS)
    assert ranked[-1]["name"] == "Bob"


def test_details_key_present():
    ranked = rankCandidates(CANDIDATES, JOB_SKILLS)
    for result in ranked:
        assert "details" in result
        assert "requiredMatches" in result["details"]
        assert "optionalMatches" in result["details"]
        assert "missingRequired" in result["details"]


def test_result_keys():
    ranked = rankCandidates(CANDIDATES, JOB_SKILLS)
    for result in ranked:
        assert set(result.keys()) == {"name", "score", "details"}


def test_empty_candidates():
    ranked = rankCandidates([], JOB_SKILLS)
    assert ranked == []


def test_single_candidate():
    ranked = rankCandidates(
        [{"name": "Alice", "skills": ["python", "sql"]}],
        JOB_SKILLS,
    )
    assert len(ranked) == 1
    assert ranked[0]["name"] == "Alice"


def test_no_matching_candidate():
    ranked = rankCandidates(
        [{"name": "Dave", "skills": ["java", "spring"]}],
        JOB_SKILLS,
    )
    assert ranked[0]["score"] == 0


def test_all_tied_scores_returns_all():
    candidates = [
        {"name": "X", "skills": ["python"]},
        {"name": "Y", "skills": ["python"]},
    ]
    ranked = rankCandidates(candidates, JOB_SKILLS)
    assert len(ranked) == 2


def test_score_is_integer():
    ranked = rankCandidates(CANDIDATES, JOB_SKILLS)
    for result in ranked:
        assert isinstance(result["score"], int)
