from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class CallAgentInput(BaseModel):
    agent_name: str = Field(
        ...,
        description="Name of the agent to call (e.g., 'sas_analyst', 'platform_architect', 'code_translator', 'test_engineer', 'code_reviewer')",
    )
    question: str = Field(
        ...,
        description="Specific question or request for the agent. Be clear and concise about what you need.",
    )


class CallAgentTool(BaseTool):
    name: str = "call_agent"
    description: str = (
        "Request help from another agent in the crew. Use this when you need:\n"
        "- Clarification from sas_analyst about SAS code behavior or data patterns\n"
        "- Guidance from platform_architect on implementation approach\n"
        "- Code fixes from code_translator\n"
        "- Test re-runs from test_engineer\n"
        "- Validation decisions from code_reviewer\n\n"
        "Example: call_agent(agent_name='sas_analyst', question='What is the typical value range for the sales column?')"
    )
    args_schema: Type[BaseModel] = CallAgentInput

    def _run(self, agent_name: str, question: str) -> str:
        """
        Request help from another agent.

        This is a placeholder that returns a structured request.
        CrewAI will handle the actual agent delegation through its context system.
        """
        return f"[REQUEST TO {agent_name.upper()}]: {question}\n\nWaiting for response from {agent_name}..."
