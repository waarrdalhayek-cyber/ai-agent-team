"""Orchestrator — routes tasks to specialised agents and coordinates collaboration."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from typing import Callable, Dict, List, Optional, Sequence, Type, TypedDict

from dotenv import load_dotenv
from openai import OpenAI

from agents import ContentAgent, ExecutionAgent, ResearchAgent

load_dotenv()

logger = logging.getLogger("orchestrator")

AGENT_MAP: Dict[str, Type] = {
    "research": ResearchAgent,
    "content": ContentAgent,
    "execution": ExecutionAgent,
}

ROUTER_SYSTEM_PROMPT = (
    "You are an orchestration router for an AI agent team. "
    "Choose the minimal ordered sequence of agents needed to complete the user's task. "
    "Available agents: research, content, execution. "
    "Return STRICT JSON only with this schema: "
    '{"sequence": ["research"|"content"|"execution", ...]}. '
    "Use 1-3 agents in order. "
    "Use multiple agents when the task requires research, writing, and/or execution planning."
)


class OrchestrationError(RuntimeError):
    """Raised when the orchestrator cannot complete a task."""


class StepResult(TypedDict):
    agent: str
    output: str


def _require_openai_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable is not set. "
            "Set it before running the orchestrator."
        )
    return api_key


def _extract_json_object(text: str) -> str:
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1)

    object_match = re.search(r"\{.*\}", text, re.DOTALL)
    if object_match:
        return object_match.group(0)

    return text


def _fallback_sequence(task: str) -> List[str]:
    task_lower = task.lower()

    needs_research = any(
        kw in task_lower
        for kw in (
            "research",
            "find",
            "search",
            "analyse",
            "analyze",
            "summarise",
            "summarize",
            "investigate",
            "compare",
            "information",
        )
    )
    needs_content = any(
        kw in task_lower
        for kw in ("write", "draft", "create content", "article", "blog", "report", "copy")
    )
    needs_execution = any(
        kw in task_lower
        for kw in (
            "execute",
            "implement",
            "plan",
            "steps",
            "deploy",
            "run",
            "build",
            "fix",
            "automate",
        )
    )

    sequence: List[str] = []
    if needs_research:
        sequence.append("research")
    if needs_content:
        sequence.append("content")
    if needs_execution:
        sequence.append("execution")

    return sequence or ["execution"]


class Orchestrator:
    """Coordinates task routing and sequential collaboration among specialized agents."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        agent_map: Optional[Dict[str, Type]] = None,
        planner: Optional[Callable[[str], List[str]]] = None,
    ):
        self.model = model
        self.agent_map = agent_map or AGENT_MAP
        self.planner = planner

    def _plan_sequence(self, task: str) -> List[str]:
        try:
            client = OpenAI(api_key=_require_openai_api_key())
            response = client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": task},
                ],
            )

            content = response.choices[0].message.content
            if content is None:
                raise OrchestrationError("Router response did not include text content.")

            payload = json.loads(_extract_json_object(content))
            raw_sequence = payload.get("sequence", [])
            if not isinstance(raw_sequence, list):
                raise OrchestrationError("Router output is invalid: 'sequence' must be a list.")

            sequence: List[str] = []
            for item in raw_sequence[:3]:
                if isinstance(item, str):
                    candidate = item.strip().lower()
                    if candidate in self.agent_map and candidate not in sequence:
                        sequence.append(candidate)

            if sequence:
                logger.info("Router selected sequence: %s", " -> ".join(sequence))
                return sequence

            raise ValueError("Router returned no valid agents.")
        except EnvironmentError:
            raise
        except Exception as exc:
            fallback = _fallback_sequence(task)
            logger.warning(
                "Router failed (%s). Falling back to keyword routing: %s",
                exc,
                " -> ".join(fallback),
            )
            return fallback

    def _run_single_agent(self, agent_type: str, task: str) -> str:
        agent_class = self.agent_map.get(agent_type)
        if agent_class is None:
            raise ValueError(
                f"Unknown agent type '{agent_type}'. Choose from: {', '.join(self.agent_map.keys())}"
            )

        agent_name = getattr(agent_class, "__name__", str(agent_class))
        logger.info("Delegating to %s", agent_name)
        agent = agent_class(model=self.model)
        result = agent.run(task)
        logger.info("%s completed", agent_name)
        return result

    @staticmethod
    def _build_collaboration_prompt(
        original_task: str, completed_steps: Sequence[StepResult], next_agent: str
    ) -> str:
        if not completed_steps:
            return original_task

        prior_outputs = "\n\n".join(
            f"Step {index + 1} ({step['agent']}):\n{step['output']}"
            for index, step in enumerate(completed_steps)
        )
        return (
            f"Original user task:\n{original_task}\n\n"
            f"Prior agent outputs:\n{prior_outputs}\n\n"
            f"You are the {next_agent} agent in a sequence. "
            "Use prior outputs as context, keep consistency, and continue toward task completion."
        )

    def orchestrate(self, task: str, forced_agent: Optional[str] = None) -> str:
        if not task or not task.strip():
            raise ValueError("Task must be a non-empty string.")

        if forced_agent:
            normalized_agent = forced_agent.lower()
            if normalized_agent not in self.agent_map:
                raise ValueError(
                    f"Unknown agent type '{forced_agent}'. "
                    f"Choose from: {', '.join(self.agent_map.keys())}"
                )
            sequence = [normalized_agent]
        else:
            sequence = self.planner(task) if self.planner else self._plan_sequence(task)

        completed_steps: List[StepResult] = []
        for agent_type in sequence:
            prompt = self._build_collaboration_prompt(task, completed_steps, agent_type)
            output = self._run_single_agent(agent_type, prompt)
            completed_steps.append({"agent": agent_type, "output": output})

        if not completed_steps:
            raise OrchestrationError("No agent steps were executed.")

        if len(completed_steps) == 1:
            return completed_steps[0]["output"]

        summary_lines = [
            "Task completed through sequential collaboration:",
            *(f"- Step {i + 1}: {step['agent']}" for i, step in enumerate(completed_steps)),
            "",
            "Final output:",
            completed_steps[-1]["output"],
        ]
        return "\n".join(summary_lines)


def route(task: str, agent_type: str, model: str = "gpt-4o-mini") -> str:
    """Backward-compatible direct routing helper."""
    return Orchestrator(model=model).orchestrate(task=task, forced_agent=agent_type)


def orchestrate(task: str, model: str = "gpt-4o-mini") -> str:
    """Backward-compatible automatic orchestration helper."""
    return Orchestrator(model=model).orchestrate(task=task)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one task through the autonomous AI agent team.")
    parser.add_argument("task", help="Single task for the orchestrator to execute.")
    parser.add_argument(
        "--agent",
        choices=sorted(AGENT_MAP.keys()),
        default=None,
        help="Optional: force a specific agent instead of automatic routing.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model for orchestrator routing and all agents (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    try:
        _require_openai_api_key()
        result = Orchestrator(model=args.model).orchestrate(task=args.task, forced_agent=args.agent)
        print("=== Result ===")
        print(result)
    except (EnvironmentError, ValueError, RuntimeError) as exc:
        logger.error("Failed to complete task: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected failure: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
