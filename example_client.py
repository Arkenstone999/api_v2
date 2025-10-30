#!/usr/bin/env python3
"""Example client for CrewSasToSparkSql API."""
import requests
import time
import sys
from pathlib import Path

API_URL = "http://localhost:8000"


def check_api_health():
    """Check if API is running."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def submit_job(sas_file_path: str) -> str:
    """Submit a SAS file for translation."""
    if not Path(sas_file_path).exists():
        raise FileNotFoundError(f"File not found: {sas_file_path}")

    print(f"Submitting job for: {sas_file_path}")

    with open(sas_file_path, "rb") as f:
        response = requests.post(
            f"{API_URL}/jobs",
            files={"file": (Path(sas_file_path).name, f, "text/plain")}
        )

    if response.status_code != 202:
        raise Exception(f"Job submission failed: {response.text}")

    job_data = response.json()
    print(f"✓ Job submitted successfully!")
    print(f"  Job ID: {job_data['job_id']}")
    print(f"  Status: {job_data['status']}")

    return job_data["job_id"]


def get_job_status(job_id: str) -> dict:
    """Get job status."""
    response = requests.get(f"{API_URL}/jobs/{job_id}")
    response.raise_for_status()
    return response.json()


def wait_for_completion(job_id: str, poll_interval: int = 5, max_wait: int = 600):
    """Poll job status until completion."""
    print(f"\nWaiting for job to complete (polling every {poll_interval}s)...")

    start_time = time.time()
    last_status = None

    while True:
        elapsed = time.time() - start_time

        if elapsed > max_wait:
            raise TimeoutError(f"Job did not complete within {max_wait} seconds")

        status = get_job_status(job_id)

        if status["status"] != last_status:
            print(f"  [{int(elapsed)}s] Status: {status['status']}")
            last_status = status["status"]

        if status["status"] == "completed":
            print(f"✓ Job completed in {int(elapsed)} seconds!")
            return status

        elif status["status"] == "failed":
            error_msg = status.get("error_message", "Unknown error")
            raise Exception(f"Job failed: {error_msg}")

        time.sleep(poll_interval)


def get_results(job_id: str) -> dict:
    """Get job results."""
    print("\nRetrieving results...")
    response = requests.get(f"{API_URL}/jobs/{job_id}/results")
    response.raise_for_status()
    return response.json()


def display_results(results: dict):
    """Display job results."""
    print("\n" + "="*80)
    print("JOB RESULTS")
    print("="*80)

    print(f"\nJob ID: {results['job_id']}")
    print(f"Job Name: {results['job_name']}")
    print(f"Status: {results['status']}")

    print(f"\nCompleted Tasks: {len(results['tasks'])}")
    for task_name, task_files in results["tasks"].items():
        print(f"\n  [{task_name}]")
        for filename in task_files.keys():
            print(f"    - {filename}")

    # Display generated code
    translate_task = results["tasks"].get("translate_code", {})
    if translate_task:
        print("\n" + "-"*80)
        print("GENERATED CODE")
        print("-"*80)

        for filename, content in translate_task.items():
            print(f"\nFile: {filename}")
            print("-"*40)
            # Print first 1000 characters
            preview = content[:1000]
            print(preview)
            if len(content) > 1000:
                print(f"\n... ({len(content) - 1000} more characters)")

    # Display validation results
    validation_task = results["tasks"].get("test_and_validate", {})
    if validation_task and "validation_report.json" in validation_task:
        print("\n" + "-"*80)
        print("VALIDATION REPORT")
        print("-"*80)
        print(validation_task["validation_report.json"][:500])

    # Display final approval
    approval_task = results["tasks"].get("review_and_approve", {})
    if approval_task and "final_approval.json" in approval_task:
        print("\n" + "-"*80)
        print("FINAL APPROVAL")
        print("-"*80)
        print(approval_task["final_approval.json"][:500])


def list_jobs(status_filter: str = None):
    """List all jobs."""
    params = {"status": status_filter} if status_filter else {}
    response = requests.get(f"{API_URL}/jobs", params=params)
    response.raise_for_status()
    jobs = response.json()

    print(f"\nFound {len(jobs)} job(s)")
    print("-"*80)

    for job in jobs:
        print(f"\nJob ID: {job['job_id']}")
        print(f"  Name: {job['job_name']}")
        print(f"  Status: {job['status']}")
        print(f"  Created: {job['created_at']}")
        if job.get('completed_at'):
            print(f"  Completed: {job['completed_at']}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Submit job:  python example_client.py submit <sas_file>")
        print("  Check status: python example_client.py status <job_id>")
        print("  Get results:  python example_client.py results <job_id>")
        print("  List jobs:    python example_client.py list [status]")
        sys.exit(1)

    command = sys.argv[1]

    # Check API health
    if not check_api_health():
        print(f"ERROR: API is not running at {API_URL}")
        print("Start the API with: python run_api.py")
        sys.exit(1)

    try:
        if command == "submit":
            if len(sys.argv) < 3:
                print("Usage: python example_client.py submit <sas_file>")
                sys.exit(1)

            sas_file = sys.argv[2]
            job_id = submit_job(sas_file)

            # Wait for completion
            wait_for_completion(job_id)

            # Get and display results
            results = get_results(job_id)
            display_results(results)

        elif command == "status":
            if len(sys.argv) < 3:
                print("Usage: python example_client.py status <job_id>")
                sys.exit(1)

            job_id = sys.argv[2]
            status = get_job_status(job_id)
            print(f"\nJob Status: {status['status']}")
            print(f"Job Name: {status['job_name']}")
            print(f"Created: {status['created_at']}")
            if status.get('started_at'):
                print(f"Started: {status['started_at']}")
            if status.get('completed_at'):
                print(f"Completed: {status['completed_at']}")
            if status.get('error_message'):
                print(f"Error: {status['error_message']}")

        elif command == "results":
            if len(sys.argv) < 3:
                print("Usage: python example_client.py results <job_id>")
                sys.exit(1)

            job_id = sys.argv[2]
            results = get_results(job_id)
            display_results(results)

        elif command == "list":
            status_filter = sys.argv[2] if len(sys.argv) > 2 else None
            list_jobs(status_filter)

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
