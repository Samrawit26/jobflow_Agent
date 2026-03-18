"""
Pipeline orchestrator.

Synchronous, deterministic bridge between pipelines and execution scripts.
No async, no Redis, no workers, no agents - just function calls.
"""

from typing import Any, Dict


class PipelineNotFoundError(Exception):
    """Raised when an unknown pipeline is requested."""
    pass


class PipelineExecutionError(Exception):
    """Raised when a pipeline execution fails."""
    pass


def run_pipeline(pipeline_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a pipeline synchronously.
    """

    if pipeline_name == "job_discovery":
        return _run_job_discovery_pipeline(payload)

    elif pipeline_name == "batch_candidate_processing":
        return _run_batch_candidate_processing_pipeline(payload)

    else:
        raise PipelineNotFoundError(
            f"Unknown pipeline: {pipeline_name}. "
            f"Supported pipelines: job_discovery, batch_candidate_processing"
        )


def _run_job_discovery_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the real job discovery pipeline.
    """

    try:
        from pipelines.job_discovery import run_job_discovery
        from jobflow.app.core.job_model import JobPosting

        # Normalise the raw payload (alias resolution, salary parsing, trim).
        normalised = JobPosting.from_raw(payload).to_dict()
        normalised.pop("raw", None)

        candidate_or_query = payload.get("candidate_or_query") or payload

        discovery = run_job_discovery(
            candidate_or_query=candidate_or_query,
            sources=payload.get("sources", []),
            match_jobs=payload.get("match_jobs", False),
            candidate_folder=payload.get("candidate_folder"),
        )

        # Normalised payload fields underpin the response; discovery keys
        # (jobs, counts, query, …) are layered on top.
        data = {**normalised, **discovery}

        return {
            "status": "success",
            "pipeline": "job_discovery",
            "data": data,
        }

    except Exception as e:
        raise PipelineExecutionError(
            f"Job discovery pipeline failed: {str(e)}"
        ) from e


def _run_batch_candidate_processing_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the batch candidate processing pipeline.
    """

    try:
        # ✅ CORRECT IMPORT
        from pipelines.batch_candidate_processing import run

        result = run(payload)

        return {
            "status": "success",
            "pipeline": "batch_candidate_processing",
            "data": result,
        }

    except Exception as e:
        raise PipelineExecutionError(
            f"Batch candidate processing pipeline failed: {str(e)}"
        ) from e
