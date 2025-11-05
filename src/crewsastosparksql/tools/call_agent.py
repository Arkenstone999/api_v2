from typing import Type, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CallAgentInput(BaseModel):
    agent_name: str = Field(
        ...,
        description="Name of the agent to consult (sas_analyst, platform_architect, code_translator, test_engineer, code_reviewer)",
    )
    question: str = Field(
        ...,
        description="Specific question. Be clear and reference specific files or data when needed.",
    )


class CallAgentTool(BaseTool):
    name: str = "call_agent"
    description: str = (
        "Consult another agent's expertise. The agent will respond based on their role and any work they've completed. "
        "Use when you need domain-specific insights or clarifications."
    )
    args_schema: Type[BaseModel] = CallAgentInput

    base_dir: str = "."
    llm: Any = None
    agents_config: dict = {}

    def _get_agent_outputs(self, agent_name: str) -> str:
        """Read any outputs the target agent has created"""
        task_map = {
            "sas_analyst": "analyze_sas",
            "platform_architect": "decide_platform",
            "code_translator": "translate_code",
            "test_engineer": "test_and_validate",
            "code_reviewer": "review_and_approve",
        }

        task_dir = task_map.get(agent_name)
        if not task_dir:
            return ""

        outputs = []
        jobs_dir = Path(self.base_dir) / "jobs"

        if jobs_dir.exists():
            for job_path in jobs_dir.iterdir():
                if not job_path.is_dir():
                    continue
                agent_output_dir = job_path / "tasks" / task_dir
                if agent_output_dir.exists():
                    for file in agent_output_dir.glob("*"):
                        if file.is_file() and file.suffix in [".json", ".txt", ".sql", ".py"]:
                            try:
                                outputs.append(f"=== {file.name} ===\n{file.read_text()[:2000]}")
                            except Exception:
                                pass

        return "\n\n".join(outputs) if outputs else ""

    def _run(self, agent_name: str, question: str) -> str:
        """Consult the target agent"""
        agent_cfg = self.agents_config.get(agent_name, {})
        if not agent_cfg:
            return f"Error: Unknown agent '{agent_name}'. Available: sas_analyst, platform_architect, code_translator, test_engineer, code_reviewer"

        # Get any outputs the agent has produced
        agent_outputs = self._get_agent_outputs(agent_name)

        # Build consultation prompt
        system_prompt = f"""You are the {agent_cfg.get('role', agent_name)}.

GOAL: {agent_cfg.get('goal', '')}
EXPERTISE: {agent_cfg.get('backstory', '')}

{'YOUR PREVIOUS WORK:' if agent_outputs else 'You have not produced any outputs yet.'}
{agent_outputs}

Respond concisely and directly based on your expertise. If you need specific information to answer, say so."""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
            response = self.llm.call(messages)
            logger.info(f"Agent {agent_name} consulted successfully")
            return str(response)

        except Exception as e:
            logger.error(f"Error consulting {agent_name}: {e}")
            return f"Unable to consult {agent_name} at this time. Consider reading their output files directly."
