import logging
from datetime import datetime
from pathlib import Path

from crewsastosparksql.crew import Crewsastosparksql
from crewsastosparksql.main import ensure_task_dirs
from crewsastosparksql.validation import TaskValidator

logger = logging.getLogger(__name__)


class TranslationResult:
    def __init__(self, code: str, rationale: str, execution_time: float):
        self.code = code
        self.rationale = rationale
        self.execution_time = execution_time


class TranslationService:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def translate(self, sas_code: str, job_name: str, max_retries: int = 2) -> TranslationResult:
        start_time = datetime.now()
        ensure_task_dirs(self.output_dir, job_name)

        sas_file_path = Path(self.output_dir) / "jobs" / job_name / "input.sas"
        sas_file_path.parent.mkdir(parents=True, exist_ok=True)
        sas_file_path.write_text(sas_code)

        inputs = {
            "sas_file_path": str(sas_file_path),
            "job_name": job_name,
            "current_year": str(datetime.now().year),
        }

        for attempt in range(max_retries):
            try:
                crew = Crewsastosparksql(output_dir=self.output_dir)
                result = crew.crew().kickoff(inputs=inputs)

                validator = TaskValidator(self.output_dir, job_name)
                validation_results = validator.validate_all()
                failed_tasks = [task for task, success in validation_results.items() if not success]

                if not failed_tasks:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    return self._extract_result(job_name, execution_time)

                if "translate_code" in failed_tasks:
                    if validator.fix_translate_code():
                        failed_tasks.remove("translate_code")

                if not failed_tasks:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    return self._extract_result(job_name, execution_time)

                if attempt < max_retries - 1:
                    logger.warning(f"Retrying translation: {failed_tasks}")
                else:
                    raise Exception(f"Translation validation failed: {failed_tasks}")

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                else:
                    raise

    def _extract_result(self, job_name: str, execution_time: float) -> TranslationResult:
        import json

        tasks_dir = Path(self.output_dir) / "jobs" / job_name / "tasks"
        translate_dir = tasks_dir / "translate_code"
        decision_file = tasks_dir / "decide_platform" / "decision.json"

        code = ""
        rationale = ""

        platform = "pyspark"
        if decision_file.exists():
            try:
                decision_data = json.loads(decision_file.read_text())
                platform_choice = decision_data.get("platform_choice", "PySpark").lower()
                platform = "sql" if "sql" in platform_choice else "pyspark"
            except Exception as e:
                logger.warning(f"Could not read decision file: {e}")

        code_file_ext = ".sql" if platform == "sql" else ".py"
        code_file = translate_dir / f"{job_name}{code_file_ext}"

        if code_file.exists():
            code = code_file.read_text()
        else:
            logger.warning(f"Expected code file not found: {code_file}")
            if translate_dir.exists():
                for file_path in translate_dir.iterdir():
                    if file_path.is_file() and file_path.suffix in [".sql", ".py"]:
                        code = file_path.read_text()
                        break

        rationale_file = tasks_dir / "review_and_approve" / "final_approval.json"
        if rationale_file.exists():
            try:
                approval_data = json.loads(rationale_file.read_text())
                rationale = approval_data.get("quality_assessment", "")
            except Exception as e:
                logger.warning(f"Could not read rationale: {e}")

        return TranslationResult(code=code, rationale=rationale, execution_time=execution_time)
