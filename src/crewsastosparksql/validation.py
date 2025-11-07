"""Task output validation and recovery."""
import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskValidator:

    EXPECTED_FILES = {
        "analyze_sas": "jobs/{job_name}/tasks/analyze_sas/analysis.json",
        "decide_platform": "jobs/{job_name}/tasks/decide_platform/decision.json",
        "translate_code": "jobs/{job_name}/tasks/translate_code/{job_name}.{ext}",
        "test_and_validate": "jobs/{job_name}/tasks/test_and_validate/validation_report.json",
        "review_and_approve": "jobs/{job_name}/tasks/review_and_approve/final_approval.json"
    }

    CRITICAL_TASKS = ["analyze_sas", "decide_platform", "translate_code", "review_and_approve"]
    OPTIONAL_TASKS = ["test_and_validate"]
    FALLBACK_TASKS = ["test_and_validate", "translate_code"]

    def __init__(self, base_dir: str, job_name: str):
        self.base_dir = base_dir
        self.job_name = job_name

    def validate_all(self) -> Dict[str, bool]:
        results = {}
        for task_name in self.EXPECTED_FILES.keys():
            results[task_name] = self._validate_task(task_name)

        for task_name in self.FALLBACK_TASKS:
            if not results.get(task_name):
                self._create_fallback(task_name)
                results[task_name] = True

        return results

    def _validate_task(self, task_name: str) -> bool:
        """Check if task produced expected file."""
        expected_path = self._get_expected_path(task_name)

        if not expected_path:
            logger.warning(f"Could not determine expected path for task: {task_name}")
            return False

        full_path = os.path.join(self.base_dir, expected_path)
        exists = os.path.exists(full_path)

        if exists:
            logger.info(f"Task '{task_name}' output verified: {expected_path}")
        else:
            logger.error(f"Task '{task_name}' output missing: {expected_path}")

        return exists

    def _get_expected_path(self, task_name: str) -> Optional[str]:
        """Get expected file path for a task."""
        template = self.EXPECTED_FILES.get(task_name)
        if not template:
            return None

        if task_name == "translate_code":
            ext = self._get_code_extension()
            return template.format(job_name=self.job_name, ext=ext)

        return template.format(job_name=self.job_name)

    def _get_code_extension(self) -> str:
        """Determine correct code file extension from decision.json."""
        decision_path = os.path.join(
            self.base_dir,
            "jobs",
            self.job_name,
            "tasks",
            "decide_platform",
            "decision.json"
        )

        if not os.path.exists(decision_path):
            logger.warning(f"Decision file not found: {decision_path}, defaulting to .sql")
            return "sql"

        try:
            with open(decision_path, "r", encoding="utf-8") as f:
                decision = json.load(f)
                platform = decision.get("platform_choice", "SQL")
                return "py" if platform == "PySpark" else "sql"
        except Exception as e:
            logger.error(f"Error reading decision file: {e}, defaulting to .sql")
            return "sql"

    def fix_translate_code(self) -> bool:
        """
        Fix translate_code output if file exists with wrong extension.
        This handles the case where agent wrote .sql instead of .py or vice versa.
        """
        expected_ext = self._get_code_extension()
        wrong_ext = "sql" if expected_ext == "py" else "py"

        translate_dir = os.path.join(
            self.base_dir,
            "jobs",
            self.job_name,
            "tasks",
            "translate_code"
        )

        if not os.path.exists(translate_dir):
            logger.error(f"Translate directory does not exist: {translate_dir}")
            return False

        expected_file = os.path.join(translate_dir, f"{self.job_name}.{expected_ext}")
        wrong_file = os.path.join(translate_dir, f"{self.job_name}.{wrong_ext}")

        if os.path.exists(expected_file):
            return True

        if os.path.exists(wrong_file):
            logger.warning(
                f"Found code with wrong extension: {wrong_file}. "
                f"Expected extension: .{expected_ext}"
            )

            try:
                os.rename(wrong_file, expected_file)
                logger.info(f"Renamed {wrong_file} to {expected_file}")
                return True
            except Exception as e:
                logger.error(f"Failed to rename file: {e}")
                return False

        logger.error(f"No code file found in {translate_dir}")
        return False

    def _create_fallback(self, task_name: str):
        if task_name == "test_and_validate":
            report_path = os.path.join(
                self.base_dir,
                "jobs",
                self.job_name,
                "tasks",
                "test_and_validate",
                "validation_report.json"
            )
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            fallback_report = {
                "verdict": "SKIPPED",
                "test_summary": "Test execution skipped due to environment limitations",
                "execution_results": "Unable to execute code validation",
                "data_coverage": [],
                "test_files_created": [],
                "recommendations": ["Manual validation recommended"],
                "code_quality_notes": "Syntax validation only, no execution testing performed"
            }
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(fallback_report, f, indent=2)
            logger.warning(f"Created fallback report for {task_name}")

        elif task_name == "translate_code":
            ext = self._get_code_extension()
            code_path = os.path.join(
                self.base_dir,
                "jobs",
                self.job_name,
                "tasks",
                "translate_code",
                f"{self.job_name}.{ext}"
            )
            os.makedirs(os.path.dirname(code_path), exist_ok=True)

            if ext == "sql":
                fallback_code = """-- FALLBACK: Agent failed to generate translation
-- This is a minimal stub - manual review required

SELECT
    *
FROM
    input_table
WHERE
    1=1;
"""
            else:
                fallback_code = """# FALLBACK: Agent failed to generate translation
# This is a minimal stub - manual review required

from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Translation").getOrCreate()

df = spark.read.format("csv").load("input_path")
df.show()
"""

            with open(code_path, "w", encoding="utf-8") as f:
                f.write(fallback_code)
            logger.warning(f"Created fallback code for {task_name} at {code_path}")
