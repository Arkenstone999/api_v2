import os
import yaml
import logging
import litellm
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task, LLM
from crewsastosparksql.tools.file_writer import FileWriterTool
from crewsastosparksql.tools.file_reader import FileReaderTool
from crewsastosparksql.tools.call_agent import CallAgentTool

load_dotenv()
logger = logging.getLogger(__name__)

litellm.drop_params = True
litellm.set_verbose = False
llm = LLM(
    model=f"azure/{os.getenv('AZURE_OPENAI_DEPLOYMENT')}",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    max_retries=5,
    timeout=180,
)


def load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        logger.warning(f"YAML file not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Crewsastosparksql:
    def __init__(self, output_dir: str | None = None):
        self.output_dir = output_dir or os.getcwd()
        logger.info(f"Initializing CrewAI workflow with output_dir: {self.output_dir}")

        config_dir = os.path.join(os.path.dirname(__file__), "config")
        agents_cfg = load_yaml(os.path.join(config_dir, "agents.yaml"))
        tasks_cfg = load_yaml(os.path.join(config_dir, "tasks.yaml"))

        file_writer = FileWriterTool(base_dir=self.output_dir)
        file_reader = FileReaderTool()
        call_agent = CallAgentTool(
            base_dir=self.output_dir,
            llm=llm,
            agents_config=agents_cfg
        )

        tools_map = {
            "file_writer": file_writer,
            "file_reader": file_reader,
            "call_agent": call_agent,
        }

        logger.info(f"Loaded {len(agents_cfg)} agents, {len(tasks_cfg)} tasks")

        self.agents_dict: dict[str, Agent] = {}
        for name, cfg in agents_cfg.items():
            if not isinstance(cfg, dict):
                continue

            tools = []
            if "tools" in cfg and isinstance(cfg["tools"], list):
                for tool_name in cfg["tools"]:
                    if tool_name in tools_map:
                        tools.append(tools_map[tool_name])
                    else:
                        logger.warning(f"Unknown tool '{tool_name}' for agent '{name}'")

            agent_params = {
                "role": cfg.get("role", name),
                "goal": cfg.get("goal", ""),
                "backstory": cfg.get("backstory", ""),
                "llm": llm,
                "verbose": cfg.get("verbose", True),
                "allow_delegation": cfg.get("allow_delegation", False),
                "tools": tools,
            }

            if "max_iter" in cfg:
                agent_params["max_iter"] = cfg["max_iter"]
            if "max_execution_time" in cfg:
                agent_params["max_execution_time"] = cfg["max_execution_time"]
            if "max_retry_limit" in cfg:
                agent_params["max_retry_limit"] = cfg["max_retry_limit"]
            if "cache" in cfg:
                agent_params["cache"] = cfg["cache"]
            if "respect_context_window" in cfg:
                agent_params["respect_context_window"] = cfg["respect_context_window"]
            if "allow_code_execution" in cfg:
                agent_params["allow_code_execution"] = cfg["allow_code_execution"]
            if "reasoning" in cfg:
                agent_params["reasoning"] = cfg["reasoning"]
            if "max_reasoning_attempts" in cfg:
                agent_params["max_reasoning_attempts"] = cfg["max_reasoning_attempts"]

            self.agents_dict[name] = Agent(**agent_params)
            logger.info(f"Created agent: {name} with {len(tools)} tools")

        self.tasks_list: list[Task] = []
        self.tasks_dict: dict[str, Task] = {}

        for task_name, task_config in tasks_cfg.items():
            if not isinstance(task_config, dict) or "agent" not in task_config:
                continue

            agent_name = task_config["agent"]
            assigned_agent = self.agents_dict.get(agent_name)
            if not assigned_agent:
                raise ValueError(f"Unknown agent '{agent_name}' in task '{task_name}'")

            context_tasks = []
            if "context" in task_config and isinstance(task_config["context"], list):
                for context_task_name in task_config["context"]:
                    if context_task_name in self.tasks_dict:
                        context_tasks.append(self.tasks_dict[context_task_name])
                    else:
                        logger.warning(
                            f"Context task '{context_task_name}' not found for task '{task_name}'"
                        )

            task = Task(
                description=task_config.get("description", ""),
                expected_output=task_config.get("expected_output", ""),
                agent=assigned_agent,
                context=context_tasks,
                verbose=True,
            )
            self.tasks_list.append(task)
            self.tasks_dict[task_name] = task
            logger.info(
                f"Created task: {task_name} (agent: {agent_name}, contexts: {len(context_tasks)})"
            )

        logger.info(
            f"Workflow initialized with {len(self.agents_dict)} agents and {len(self.tasks_list)} tasks"
        )

    def crew(self) -> Crew:
        logger.info("Building Crew with sequential process")

        return Crew(
            agents=list(self.agents_dict.values()),
            tasks=self.tasks_list,
            process=Process.sequential,
            verbose=True,
            max_rpm=30,
        )
