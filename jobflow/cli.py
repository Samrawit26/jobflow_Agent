import argparse
import json
import sys

from jobflow.app.core.plan_review_runner import review_directive
from jobflow.app.core.approval_artifact import create_approval
from jobflow.app.core.plan_executor import execute_from_directive


def run_job_discovery(args):
    review = review_directive("job_discovery", auto_approve=True)
    approval = create_approval(review["plan"], "policy")

    payload = {
        "candidate_or_query": {
            "desired_title": args.title,
            "skills_years": {args.skill: args.years} if args.skill else {},
        },
        "sources": [],
        "match_jobs": args.match_jobs,
    }

    result = execute_from_directive("job_discovery", approval, payload)

    print(json.dumps(result, indent=2))


def run_batch(args):
    from jobflow.app.core.batch_runner import run_batch as _run_batch
    from jobflow.app.core.file_job_source import FileJobSource

    source = FileJobSource("jobs", args.jobs)

    try:
        result = _run_batch(
            candidates_dir=args.candidates,
            job_sources=[source],
            out_dir=args.out,
            match_jobs=not args.no_match,
            export_apply_packs=not args.no_apply_packs,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Processed:   {result['processed']}")
    print(f"Succeeded:   {result['succeeded']}")
    print(f"Failed:      {result['failed']}")
    print(f"Summary CSV: {result['summary_path']}")
    print(f"Errors JSON: {result['errors_path']}")


def main():
    parser = argparse.ArgumentParser(description="JobFlow CLI")

    subparsers = parser.add_subparsers(dest="command")

    # job_discovery command
    job_parser = subparsers.add_parser("job_discovery", help="Run job discovery for a candidate")
    job_parser.add_argument("--title", required=True, help="Desired job title")
    job_parser.add_argument("--skill", help="Primary skill")
    job_parser.add_argument("--years", type=int, default=0, help="Years of experience")
    job_parser.add_argument("--match-jobs", action="store_true", help="Enable job matching")

    # batch command
    batch_parser = subparsers.add_parser("batch", help="Run batch candidate processing")
    batch_parser.add_argument("--candidates", required=True, help="Path to candidate folders directory")
    batch_parser.add_argument("--jobs", required=True, help="Path to jobs JSON file")
    batch_parser.add_argument("--out", required=True, help="Output directory")
    batch_parser.add_argument("--no-match", action="store_true", help="Disable job matching")
    batch_parser.add_argument("--no-apply-packs", action="store_true", help="Disable apply pack generation")

    args = parser.parse_args()

    if args.command == "job_discovery":
        run_job_discovery(args)
    elif args.command == "batch":
        run_batch(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
