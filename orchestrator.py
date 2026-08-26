"""Orchestrator for routing work across the specialized agent team."""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from agents import ContentAgent, ExecutionAgent, ResearchAgent

AGENT_MAP = {
    "research": ResearchAgent,
    "content": ContentAgent,
    "execution": ExecutionAgent,
}

AGENT_ORDER = {
    "research": 0,
    "content": 1,
    "execution": 2,
}

ROUTER_SYSTEM_PROMPT = """You are an orchestration planner for an autonomous AI agent team.
You must choose the smallest useful workflow using these agents:
- research: gather facts, analyze information, identify uncertainties
- content: draft, rewrite, summarize, or structure polished written output
- execution: turn work into concrete actions, implementation steps, or an actionable final answer

Rules:
- Return JSON only.
- The JSON schema is {"workflow": ["research"|"content"|"execution", ...], "reason": "string"}.
- Choose one or more agents.
- Use sequential collaboration only when it improves the result.
- If research, content, and execution are all needed, order them as research, content, execution.
- Never include an unknown agent.
"""

SYNTHESIS_SYSTEM_PROMPT = """You are the lead orchestrator of an autonomous AI agent team.
Combine the outputs from the specialist agents into one final response for the user.
Preserve useful details, remove duplication, and clearly present the final answer.
"""


@dataclass
class WorkflowPlan:
    workflow: list[str]
    reason: str


class Orchestrator:
    """Routes a task to one or more specialized agents."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        client: Any | None = None,
        agent_model: str | None = None,
    ) -> None:
        self.model = model
        self.agent_model = agent_model or model
        self.logger = logging.getLogger("orchestrator")
        self.client = client or OpenAI(api_key=self._get_api_key())

    @staticmethod
    def _get_api_key() -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY environment variable is not set."
            )
        return api_key

    @staticmethod
    def _extract_json(content: str) -> dict[str, Any]:
        candidate = content.strip()
        fenced_match = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
        if fenced_match:
            candidate = fenced_match.group(1).strip()
        return json.loads(candidate)

    def _plan_workflow(self, task: str) -> WorkflowPlan:
        self.logger.info("Planning workflow")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": task},
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on SDK/runtime details
            self.logger.exception("Workflow planning failed")
            raise RuntimeError(f"Failed to plan agent workflow: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("Failed to plan agent workflow: empty model response.")

        try:
            payload = self._extract_json(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Failed to parse orchestrator workflow response: {content!r}"
            ) from exc

        raw_workflow = payload.get("workflow")
        if not isinstance(raw_workflow, list) or not raw_workflow:
            raise RuntimeError(
                f"Invalid workflow returned by orchestrator: {payload!r}"
            )

        unique_workflow = []
        for item in raw_workflow:
            if item not in AGENT_MAP:
                raise RuntimeError(f"Unknown agent in workflow: {item!r}")
            if item not in unique_workflow:
                unique_workflow.append(item)

        unique_workflow.sort(key=lambda agent_name: AGENT_ORDER[agent_name])
        reason = payload.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "Selected by the orchestrator."

        self.logger.info("Workflow selected: %s", " -> ".join(unique_workflow))
        return WorkflowPlan(workflow=unique_workflow, reason=reason.strip())

    def _build_collaboration_context(self, results: list[tuple[str, str]]) -> str | None:
        if not results:
            return None
        return "\n\n".join(
            f"{agent_type.upper()} OUTPUT:\n{output}" for agent_type, output in results
        )

    def _run_agent(self, agent_type: str, task: str, results: list[tuple[str, str]]) -> str:
        agent_class = AGENT_MAP[agent_type]
        self.logger.info("Delegating to %s", agent_class.__name__)
        agent = agent_class(model=self.agent_model, client=self.client)
        return agent.run(task, collaboration_context=self._build_collaboration_context(results))

    def _synthesize(self, task: str, workflow: list[str], results: list[tuple[str, str]]) -> str:
        if len(results) == 1:
            return results[0][1]

        self.logger.info("Synthesizing final response")
        collaboration_context = self._build_collaboration_context(results)
        prompt = (
            f"Original task:\n{task}\n\n"
            f"Workflow used: {' -> '.join(workflow)}\n\n"
            f"Specialist outputs:\n{collaboration_context}\n\n"
            "Produce the final answer for the user."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on SDK/runtime details
            self.logger.exception("Final synthesis failed")
            raise RuntimeError(f"Failed to synthesize the final response: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("Failed to synthesize the final response: empty model response.")
        return content.strip()

    def route(self, task: str, agent_type: str) -> str:
        """Run a task through one explicit specialized agent."""
        if agent_type not in AGENT_MAP:
            raise ValueError(
                f"Unknown agent type '{agent_type}'. Choose from: {', '.join(AGENT_MAP)}"
            )
        result = self._run_agent(agent_type, task, [])
        self.logger.info("Finished with %s", agent_type)
        return result

    def orchestrate(self, task: str) -> tuple[WorkflowPlan, str]:
        """Plan the workflow, execute it, and return the final answer."""
        plan = self._plan_workflow(task)
        results: list[tuple[str, str]] = []

        for agent_type in plan.workflow:
            output = self._run_agent(agent_type, task, results)
            results.append((agent_type, output))

        return plan, self._synthesize(task, plan.workflow, results)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s: %(name)s: %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one task through the autonomous AI agent team."
    )
    parser.add_argument("task", nargs="+", help="Task for the orchestrator to execute.")
    parser.add_argument(
        "--agent",
        choices=tuple(AGENT_MAP),
        help="Optional explicit agent override instead of automatic orchestration.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use for the orchestrator and agents.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    task = " ".join(args.task).strip()
    if not task:
        parser.error("Task cannot be empty.")

    try:
        orchestrator = Orchestrator(model=args.model)
        if args.agent:
            print(f"Workflow: {args.agent}")
            result = orchestrator.route(task, args.agent)
        else:
            plan, result = orchestrator.orchestrate(task)
            print(f"Workflow: {' -> '.join(plan.workflow)}")
            print(f"Reason: {plan.reason}")
        print("\n=== Result ===")
        print(result)
        return 0
    except (EnvironmentError, RuntimeError, ValueError) as exc:
        logging.getLogger("cli").error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
