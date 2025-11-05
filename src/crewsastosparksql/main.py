import sys
import os
import yaml
import logging
from datetime import datetime
from crewsastosparksql.crew import Crewsastosparksql
from crewsastosparksql.validation import TaskValidator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ensure_task_dirs(project_root: str, job_name: str) -> None:
    """Create required directories and initialize workflow log."""
    config_path = os.path.join(os.path.dirname(__file__), "config", "tasks.yaml")
    if not os.path.exists(config_path):
        logger.warning(f"Missing tasks.yaml at {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        tasks_yaml = yaml.safe_load(f) or {}

    job_dir = os.path.join(project_root, "jobs", job_name)
    task_root = os.path.join(job_dir, "tasks")
    logs_dir = os.path.join(job_dir, "logs")
    os.makedirs(task_root, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    for task_name, task_cfg in tasks_yaml.items():
        if isinstance(task_cfg, dict):
            os.makedirs(os.path.join(task_root, task_name), exist_ok=True)

    with open(os.path.join(logs_dir, "workflow.log"), "w", encoding="utf-8") as f:
        f.write(f"Workflow started: {datetime.now().isoformat()}\n")
        f.write(f"Job: {job_name}\n")
        f.write("-" * 80 + "\n")

    logger.info(f"Initialized directories for job '{job_name}'")


def run() -> None:

    if len(sys.argv) < 2:
        print("Usage: python -m crewsastosparksql.main path/to/file.sas")
        sys.exit(1)

    sas_file_path = sys.argv[1]
    if not os.path.exists(sas_file_path):
        logger.error(f"SAS file not found: {sas_file_path}")
        sys.exit(1)

    job_name = os.path.splitext(os.path.basename(sas_file_path))[0]
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    logger.info(f"Starting workflow for job '{job_name}'")

    ensure_task_dirs(project_root, job_name)
    inputs = {
        "sas_file_path": os.path.abspath(sas_file_path),
        "job_name": job_name,
        "current_year": str(datetime.now().year),
    }

    max_retries = 2
    result = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Running workflow (attempt {attempt + 1}/{max_retries})")

            crew = Crewsastosparksql(output_dir=project_root)
            result = crew.crew().kickoff(inputs=inputs)

            validator = TaskValidator(project_root, job_name)
            validation_results = validator.validate_all()

            failed_tasks = [task for task, success in validation_results.items() if not success]

            if not failed_tasks:
                logger.info("All tasks validated successfully")
                print(result)
                return

            logger.warning(f"Tasks failed validation: {failed_tasks}")

            if "translate_code" in failed_tasks:
                logger.info("Attempting to fix translate_code file path issue")
                if validator.fix_translate_code():
                    validation_results["translate_code"] = True
                    failed_tasks.remove("translate_code")

            if not failed_tasks:
                logger.info("All tasks validated after fixes")
                print(result)
                return

            if attempt < max_retries - 1:
                logger.warning(f"Retrying workflow due to failed tasks: {failed_tasks}")
            else:
                logger.error(f"Tasks failed validation after all retries: {failed_tasks}")
                sys.exit(1)

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Workflow failed (attempt {attempt + 1}): {e}")
            else:
                logger.exception(f"Workflow failed after all retries: {e}")
                sys.exit(1)


if __name__ == "__main__":
    run()
