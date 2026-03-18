"""
Batch candidate processing runner.

Processes multiple candidate folders and generates aggregated results.
"""

import csv
import json
import re
import traceback
from pathlib import Path


def discover_candidate_folders(candidates_dir: str) -> list[str]:
    """
    Discover candidate folders in directory.

    Returns sorted list of immediate subdirectories that appear to be
    candidate folders (contain either .xlsx or resume files).

    Args:
        candidates_dir: Path to directory containing candidate folders

    Returns:
        Sorted list of absolute paths to candidate folders
    """
    candidates_path = Path(candidates_dir)

    if not candidates_path.exists() or not candidates_path.is_dir():
        return []

    candidate_folders = []

    for item in candidates_path.iterdir():
        if not item.is_dir():
            continue

        # Check if it looks like a candidate folder
        # Must have either .xlsx OR resume files (.txt, .md, .docx)
        has_xlsx = any(item.glob("*.xlsx"))
        has_resume = (
            any(item.glob("*.txt"))
            or any(item.glob("*.md"))
            or any(item.glob("*.docx"))
        )

        if has_xlsx or has_resume:
            candidate_folders.append(str(item.absolute()))

    return sorted(candidate_folders)


def run_batch(
    candidates_dir: str,
    job_sources: list,
    out_dir: str,
    match_jobs: bool = True,
    export_apply_packs: bool = True,
    top_n: int = 25,
    company_domains: set[str] | None = None,
    matcher=None,
) -> dict:
    """
    Run batch candidate processing.

    Processes all candidate folders and generates:
    - Per-candidate results JSON files
    - Summary CSV with key metrics
    - Errors JSON with any failures
    - Apply packs with submission-ready outputs (optional)

    Args:
        candidates_dir: Directory containing candidate folders
        job_sources: List of JobSource instances for job aggregation
        out_dir: Output directory for results
        match_jobs: Whether to compute match scores (default True)
        export_apply_packs: Whether to generate apply pack exports (default True)
        top_n: Number of top jobs to include in apply packs (default 25)
        company_domains: Optional set of known company domains for URL allowlisting
        matcher: Optional callable to inject for AI matching (default uses env key)

    Returns:
        Dict with:
        - processed: number of candidates processed
        - succeeded: number of successful candidates
        - failed: number of failed candidates
        - summary_path: path to summary.csv
        - errors_path: path to errors.json
        - results_dir: path to results directory
        - apply_packs_dir: path to apply packs directory (if enabled)
    """
    from pipelines.job_discovery import run_job_discovery

    # Create output directories
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    results_dir = out_path / "results"
    results_dir.mkdir(exist_ok=True)

    apply_packs_dir = out_path / "apply_packs" if export_apply_packs else None
    if apply_packs_dir:
        apply_packs_dir.mkdir(exist_ok=True)

    # Discover candidate folders
    candidate_folders = discover_candidate_folders(candidates_dir)

    if not candidate_folders:
        _write_summary_csv(str(out_path / "summary.csv"), [], export_apply_packs)
        _write_errors_json(str(out_path / "errors.json"), [])
        result = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "summary_path": str(out_path / "summary.csv"),
            "errors_path": str(out_path / "errors.json"),
            "results_dir": str(results_dir),
        }
        if apply_packs_dir:
            result["apply_packs_dir"] = str(apply_packs_dir)
        return result

    summary_rows = []
    errors = []
    processed = 0
    succeeded = 0
    failed = 0

    for folder in candidate_folders:
        processed += 1
        folder_name = Path(folder).name

        # ── 1. Run discovery ────────────────────────────────────────────────
        try:
            discovery_kwargs: dict = {
                "sources": job_sources,
                "candidate_folder": folder,
                "match_jobs": match_jobs,
            }
            if matcher is not None:
                discovery_kwargs["matcher"] = matcher

            result = run_job_discovery(**discovery_kwargs)

        except Exception as e:
            errors.append({
                "folder": folder_name,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": _truncate_traceback(traceback.format_exc(), max_lines=20),
            })
            summary_row: dict = {
                "candidate_id": folder_name,
                "folder": folder_name,
                "num_jobs": 0,
                "num_matches": 0,
                "top_score": "",
                "num_errors": 0,
                "status": "failed",
            }
            if export_apply_packs:
                summary_row.update({
                    "num_strong_fit": 0,
                    "num_possible_fit": 0,
                    "num_weak_fit": 0,
                    "num_url_allowed": 0,
                    "num_url_manual_review": 0,
                    "num_url_blocked": 0,
                })
            summary_rows.append(summary_row)
            failed += 1
            continue

        # Discovery succeeded → count as succeeded
        succeeded += 1

        candidate_id = _extract_candidate_id(result, folder_name)
        safe_id = safe_slug(candidate_id)

        # ── 2. Write per-candidate results JSON ─────────────────────────────
        candidate_results_dir = results_dir / safe_id
        candidate_results_dir.mkdir(exist_ok=True)

        with open(candidate_results_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True)

        # ── 3. Apply pack (optional, errors do not fail the candidate) ───────
        apply_pack: dict | None = None
        if export_apply_packs and apply_packs_dir:
            try:
                from jobflow.app.core.apply_pack import build_apply_pack
                from jobflow.app.core.apply_pack_export import (
                    write_apply_pack_csv,
                    write_apply_pack_json,
                )
                from jobflow.app.core.application_queue import (
                    build_queue_rows,
                    merge_queue,
                    read_queue_csv,
                    write_queue_csv,
                )

                apply_pack = build_apply_pack(
                    result,
                    top_n=top_n,
                    company_domains=company_domains,
                )

                candidate_apply_dir = apply_packs_dir / safe_id
                candidate_apply_dir.mkdir(exist_ok=True)

                write_apply_pack_json(
                    apply_pack,
                    str(candidate_apply_dir / "applications_ready.json"),
                )
                write_apply_pack_csv(
                    apply_pack,
                    str(candidate_apply_dir / "applications_ready.csv"),
                )

                queue_path = str(candidate_apply_dir / "application_queue.csv")
                existing_queue = read_queue_csv(queue_path)
                new_queue_rows = build_queue_rows(apply_pack)
                merged_queue = merge_queue(existing_queue, new_queue_rows)
                write_queue_csv(merged_queue, queue_path)

            except Exception:
                pass  # apply pack errors never mark candidate as failed

        # ── 4. Build summary row ────────────────────────────────────────────
        counts = result.get("counts", {})
        matches = result.get("matches", [])

        num_jobs = counts.get("jobs", 0)
        num_errors = counts.get("errors", 0)
        num_matches = counts.get("matches", len(matches))
        top_score = matches[0].get("overall_score", "") if matches else ""

        summary_row = {
            "candidate_id": candidate_id,
            "folder": folder_name,
            "num_jobs": num_jobs,
            "num_matches": num_matches,
            "top_score": top_score,
            "num_errors": num_errors,
            "status": "success",
        }

        if export_apply_packs:
            num_strong_fit = 0
            num_possible_fit = 0
            num_weak_fit = 0
            if match_jobs and matches:
                for match in matches:
                    decision = match.get("decision", "")
                    if decision == "strong_fit":
                        num_strong_fit += 1
                    elif decision == "possible_fit":
                        num_possible_fit += 1
                    elif decision == "weak_fit":
                        num_weak_fit += 1

            url_review = (apply_pack or {}).get("url_review_summary", {})
            summary_row.update({
                "num_strong_fit": num_strong_fit,
                "num_possible_fit": num_possible_fit,
                "num_weak_fit": num_weak_fit,
                "num_url_allowed": url_review.get("allowed", 0),
                "num_url_manual_review": url_review.get("manual_review", 0),
                "num_url_blocked": url_review.get("blocked", 0),
            })

        summary_rows.append(summary_row)

    # ── 5. Write final output files ─────────────────────────────────────────
    summary_path = str(out_path / "summary.csv")
    _write_summary_csv(summary_path, summary_rows, export_apply_packs)

    errors_path = str(out_path / "errors.json")
    _write_errors_json(errors_path, errors)

    result = {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "summary_path": summary_path,
        "errors_path": errors_path,
        "results_dir": str(results_dir),
    }

    if apply_packs_dir:
        result["apply_packs_dir"] = str(apply_packs_dir)

    return result


def safe_slug(text: str) -> str:
    """
    Create safe filesystem slug from text.

    Rules:
    - Lowercase
    - Replace spaces with underscores
    - Keep only alphanumeric, underscore, dash
    - Collapse consecutive separators
    - Max length 80 characters
    """
    if not text:
        return "unknown"

    slug = text.lower()
    slug = slug.replace(" ", "_")
    slug = re.sub(r"[^a-z0-9_-]", "", slug)
    slug = re.sub(r"[_-]+", "_", slug)
    slug = slug.strip("_-")

    if len(slug) > 80:
        slug = slug[:80].rstrip("_-")

    return slug or "unknown"


def _extract_candidate_id(result: dict, fallback: str) -> str:
    """
    Extract candidate ID from discovery result.

    Priority: candidate.email → candidate.name → fallback (folder name)
    """
    candidate = result.get("candidate", {})
    return (
        candidate.get("email")
        or candidate.get("name")
        or fallback
    )


def _write_summary_csv(
    path: str, rows: list[dict], include_fit_counts: bool = False
) -> None:
    """Write summary CSV file."""
    fieldnames = [
        "candidate_id",
        "folder",
        "num_jobs",
        "num_matches",
        "top_score",
    ]

    if include_fit_counts:
        fieldnames.extend([
            "num_strong_fit",
            "num_possible_fit",
            "num_weak_fit",
            "num_url_allowed",
            "num_url_manual_review",
            "num_url_blocked",
        ])

    fieldnames.extend(["num_errors", "status"])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_errors_json(path: str, errors: list[dict]) -> None:
    """Write errors JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2, sort_keys=True)


def _truncate_traceback(tb: str, max_lines: int = 20) -> str:
    """Truncate traceback to max lines."""
    lines = tb.split("\n")
    if len(lines) <= max_lines:
        return tb
    return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
