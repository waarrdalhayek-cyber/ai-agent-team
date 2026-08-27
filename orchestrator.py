"""Orchestrator for routing work across the specialized agent team."""

from __future__ import annotations

import argparse
import json
import logging
import os
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
    print("--- [DIAGNOSTIC CHECK] ---")
    if not api_key:
      print("DIAGNOSTIC FAIL: OPENAI_API_KEY is missing or empty!")
      raise EnvironmentError(
          "OPENAI_API_KEY environment variable is not set."
      )
    print(
        f"DIAGNOSTIC PASS: OPENAI_API_KEY is present (Length: {len(api_key)})"
    )
    return api_key

  def plan(self, task: str) -> WorkflowPlan:
    self.logger.info("Planning workflow for task: %s", task)
    response = self.client.chat.completions.create(
        model=self.model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ],
    )
    content = response.choices[0].message.content
    if not content:
      raise ValueError("Received empty response from router model.")

    data = json.loads(content)
    workflow = data.get("workflow", [])
    reason = data.get("reason", "")

    validated_workflow = []
    seen = set()
    for step in workflow:
      if step in AGENT_MAP and step not in seen:
        validated_workflow.append(step)
        seen.add(step)

    if not validated_workflow:
      validated_workflow = ["content"]
      reason = (
          "Defaulted to content agent because no valid agents were selected."
      )

    validated_workflow.sort(key=lambda s: AGENT_ORDER.get(s, 99))
    return WorkflowPlan(workflow=validated_workflow, reason=reason)

  def synthesize(self, task: str, results: dict[str, str]) -> str:
    self.logger.info("Synthesizing results from agents")
    results_str = "\n\n".join(
        f"--- {agent_name.upper()} AGENT OUTPUT ---\n{output}"
        for agent_name, output in results.items()
    )
    prompt = f"Original Task: {task}\n\nAgent Results:\n{results_str}"
    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content
    return content if content else "No synthesis generated."

  def route(self, task: str, agent_name: str) -> str:
    if agent_name not in AGENT_MAP:
      raise ValueError(f"Unknown agent: {agent_name}")

    agent_cls = AGENT_MAP[agent_name]
    agent = agent_cls(model=self.agent_model, client=self.client)
    return agent.run(task)
  def orchestrate(self, task: str) -> tuple[WorkflowPlan, str]:
    plan = self.plan(task)
    self.logger.info(
        "Execution plan: %s (Reason: %s)", plan.workflow, plan.reason
    )

    results: dict[str, str] = {}
    context = f"Task:\n{task}"

    for agent_name in plan.workflow:
      self.logger.info("Running %s agent", agent_name)
      output = self.route(context, agent_name)
      results[agent_name] = output
      context = f"{context}\n\n{agent_name.upper()} OUTPUT:\n{output}"

    if len(results) == 1:
      final_output = list(results.values())[0]
    else:
      final_output = self.synthesize(task, results)

    return plan, final_output
def run(self, task: str) -> str:
    plan = self.plan(task)
    self.logger.info(
        "Execution plan: %s (Reason: %s)", plan.workflow, plan.reason
    )

    results: dict[str, str] = {}
    context = task

    for agent_name in plan.workflow:
      agent_cls = AGENT_MAP[agent_name]
      agent = agent_cls(model=self.agent_model, client=self.client)
      self.logger.info("Running %s agent", agent_name)
      output = agent.run(context)
      results[agent_name] = output
      context = f"{context}\n\nPrevious Agent Output ({agent_name}):\n{output}"

    if len(results) == 1:
      final_output = list(results.values())[0]
    else:
      final_output = self.synthesize(task, results)

    return final_output


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
      description="Orchestrator for autonomous AI agent team."
  )
  parser.add_argument("task", type=str, help="The task for the agents to execute.")
  parser.add_argument(
      "--model",
      type=str,
      default="gpt-4o-mini",
      help="OpenAI model for routing and synthesis.",
  )
  parser.add_argument(
      "--agent-model",
      type=str,
      default=None,
      help="OpenAI model for specialist agents.",
  )
  return parser.parse_args()


def main() -> None:
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  )
  args = parse_args()
  orchestrator = Orchestrator(model=args.model, agent_model=args.agent_model)
  final_answer = orchestrator.run(args.task)
  print("\n=== FINAL ANSWER ===")
  print(final_answer)


if __name__ == "__main__":
  main()
