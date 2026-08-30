"""Orchestrator for routing work across the specialized agent team."""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from agents import ContentAgent, ExecutionAgent, ResearchAgent, VideoAgent

AGENT_MAP = {
    "research": ResearchAgent,
    "content": ContentAgent,
    "execution": ExecutionAgent,
    "video": VideoAgent,
}

AGENT_ORDER = {
    "research": 0,
    "content": 1,
    "execution": 2,
    "video": 3,
}

ROUTER_SYSTEM_PROMPT = """You are an orchestration planner for an autonomous AI agent team.
Choose the smallest useful workflow using these agents:
- research: gather facts, analyze information, identify uncertainties
- content: draft, rewrite, summarize, or structure polished written output
- execution: turn non-video work into concrete actions or implementation
- video: understand video requests and prepare/execute video production workflows

Rules:
- Return JSON only.
- Schema: {"workflow": ["research"|"content"|"execution"|"video", ...], "reason": "string"}.
- For requests to create, produce, edit, animate, assemble, lip-sync, or render a video, include video.
- Do not use execution as a substitute for video production.
- Choose one or more agents only when useful.
- Never include an unknown agent.
"""

SYNTHESIS_SYSTEM_PROMPT = """You are the lead orchestrator of an autonomous AI agent team.
Combine specialist outputs into one final response. Preserve concrete execution results and file paths.
"""


@dataclass
class WorkflowPlan:
    workflow: list[str]
    reason: str


class Orchestrator:
    """Routes a task to one or more specialized agents."""

    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None, agent_model: str | None = None) -> None:
        self.model = model
        self.agent_model = agent_model or model
        self.logger = logging.getLogger("orchestrator")
        self.client = client or OpenAI(api_key=self._get_api_key())

    @staticmethod
    def _get_api_key() -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
        return api_key

    def plan(self, task: str) -> WorkflowPlan:
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": ROUTER_SYSTEM_PROMPT}, {"role": "user", "content": task}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Received empty response from router model.")
        data = json.loads(content)
        workflow = []
        seen = set()
        for step in data.get("workflow", []):
            if step in AGENT_MAP and step not in seen:
                workflow.append(step)
                seen.add(step)
        if not workflow:
            workflow = ["content"]
        workflow.sort(key=lambda step: AGENT_ORDER.get(step, 99))
        return WorkflowPlan(workflow=workflow, reason=data.get("reason", ""))

    def route(self, task: str, agent_name: str) -> str:
        if agent_name not in AGENT_MAP:
            raise ValueError(f"Unknown agent: {agent_name}")
        agent = AGENT_MAP[agent_name](model=self.agent_model, client=self.client)
        return agent.run(task)

    def synthesize(self, task: str, results: dict[str, str]) -> str:
        results_str = "\n\n".join(f"--- {name.upper()} AGENT OUTPUT ---\n{output}" for name, output in results.items())
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"Original Task: {task}\n\nAgent Results:\n{results_str}"},
            ],
        )
        return response.choices[0].message.content or "No synthesis generated."

    def orchestrate(self, task: str) -> tuple[WorkflowPlan, str]:
        plan = self.plan(task)
        results: dict[str, str] = {}
        context = f"Task:\n{task}"
        for agent_name in plan.workflow:
            output = self.route(context, agent_name)
            results[agent_name] = output
            context += f"\n\n{agent_name.upper()} OUTPUT:\n{output}"
        final_output = list(results.values())[0] if len(results) == 1 else self.synthesize(task, results)
        return plan, final_output

    def run(self, task: str) -> str:
        return self.orchestrate(task)[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orchestrator for autonomous AI agent team.")
    parser.add_argument("task", type=str, help="The task for the agents to execute.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    parser.add_argument("--agent-model", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    args = parse_args()
    orchestrator = Orchestrator(model=args.model, agent_model=args.agent_model)
    print("\n=== FINAL ANSWER ===")
    print(orchestrator.run(args.task))


if __name__ == "__main__":
    main()
