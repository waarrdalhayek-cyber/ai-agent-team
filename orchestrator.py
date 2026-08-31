"""Top-level manager for the hierarchical autonomous agent team."""
from __future__ import annotations
import argparse
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any
from openai import OpenAI
from agents import (
    BusinessManager, ContentAgent, CreativeLearningManager, EcommerceAgent,
    ExecutionAgent, LearningAgent, ResearchAgent, TravelAgent, VideoAgent,
)

DIVISION_MAP = {
    "creative_learning": CreativeLearningManager,
    "business": BusinessManager,
    "general": ExecutionAgent,
}
DIVISION_SPECIALISTS = {
    "creative_learning": {"content": ContentAgent, "video": VideoAgent, "learning": LearningAgent, "research": ResearchAgent},
    "business": {"travel": TravelAgent, "ecommerce": EcommerceAgent, "research": ResearchAgent},
    "general": {"execution": ExecutionAgent, "research": ResearchAgent},
}

ROUTER_SYSTEM_PROMPT = """You are the GENERAL MANAGER of a hierarchical autonomous agent team.
Route each request first to ONE division manager, then to the smallest useful set of specialists in that division.
Divisions:
- creative_learning: content, video, tutoring, curricula, driving learning, English, mathematics, mental arithmetic, Mawhiba, educational media
- business: travel, flights, hotels, restaurants, reservations, calendar, appointments, schedules, meetings, e-commerce, products, market/competitor analysis, stores, advertising, customer/order workflows
- general: other implementation/execution tasks
Specialists allowed by division:
- creative_learning: content, video, learning, research
- business: travel, ecommerce, research
- general: execution, research
Calendar, appointments, meetings, and personal schedule requests MUST route to business with travel specialist.
Return JSON only using exactly: {"division":"creative_learning|business|general","specialists":["..."],"reason":"..."}.
Use research only when fresh facts or external investigation are genuinely required. Never route directly across divisions. Never invent a specialist.
MANDATORY GLOBAL FINANCIAL RULE: Any payment, purchase, subscription, paid advertisement, ad-budget change, supplier order, refund, transfer, booking charge, or financial commitment requires explicit user approval for that specific action before execution. A general instruction to manage or automate everything is never financial approval.
"""
SYNTHESIS_SYSTEM_PROMPT = """You are the GENERAL MANAGER. Combine confirmed tool and agent results into one concise final result. Never invent calendar events or claim an external action, booking, payment, purchase, calendar write, generation, or transaction occurred unless confirmed by the executing tool/specialist. Financial actions always require the user's explicit approval for that specific action."""

@dataclass
class WorkflowPlan:
    division: str
    specialists: list[str]
    reason: str

class Orchestrator:
    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None, agent_model: str | None = None) -> None:
        self.model = model
        self.agent_model = agent_model or model
        self.logger = logging.getLogger("general_manager")
        self.client = client or OpenAI(api_key=self._get_api_key())

    @staticmethod
    def _get_api_key() -> str:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
        return key

    def plan(self, task: str) -> WorkflowPlan:
        response = self.client.chat.completions.create(model=self.model, response_format={"type": "json_object"}, messages=[{"role": "system", "content": ROUTER_SYSTEM_PROMPT}, {"role": "user", "content": task}])
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Received empty response from general manager router.")
        data = json.loads(content)
        division = data.get("division", "general")
        if division not in DIVISION_MAP:
            division = "general"
        allowed = DIVISION_SPECIALISTS[division]
        specialists, seen = [], set()
        for name in data.get("specialists", []):
            if name in allowed and name not in seen:
                specialists.append(name); seen.add(name)
        if not specialists:
            specialists = [next(iter(allowed))]
        return WorkflowPlan(division=division, specialists=specialists, reason=data.get("reason", ""))

    def _run_agent(self, cls: Any, task: str) -> str:
        return cls(model=self.agent_model, client=self.client).run(task)

    @staticmethod
    def _is_calendar_read(task: str) -> bool:
        t = task.lower()
        calendar_words = ("تقويم", "مواعيد", "موعد", "calendar", "appointments", "schedule", "meetings")
        write_words = ("أضف", "اضف", "أنشئ", "انشئ", "احذف", "الغ", "ألغي", "عدّل", "عدل", "create", "add", "delete", "cancel", "update")
        return any(w in t for w in calendar_words) and not any(w in t for w in write_words)

    def _calendar_read(self, task: str) -> str:
        """Execute a real Calendar read. Default natural-language window is next seven days."""
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=7)
        agent = TravelAgent(model=self.agent_model, client=self.client)
        events = agent.calendar_events(now.isoformat(), end.isoformat())
        if not events:
            return "CONFIRMED GOOGLE CALENDAR RESULT: No events found in the next seven days."
        compact = []
        for event in events:
            compact.append({"summary": event.get("summary", "(no title)"), "start": event.get("start", {}), "end": event.get("end", {}), "location": event.get("location")})
        return "CONFIRMED GOOGLE CALENDAR RESULT:\n" + json.dumps(compact, ensure_ascii=False)

    def route(self, task: str, agent_name: str) -> str:
        for specialists in DIVISION_SPECIALISTS.values():
            if agent_name in specialists:
                if agent_name == "travel" and self._is_calendar_read(task):
                    return self._calendar_read(task)
                return self._run_agent(specialists[agent_name], task)
        if agent_name in DIVISION_MAP:
            return self._run_agent(DIVISION_MAP[agent_name], task)
        raise ValueError(f"Unknown agent: {agent_name}")

    def synthesize(self, task: str, results: dict[str, str]) -> str:
        packed = "\n\n".join(f"--- {name.upper()} ---\n{value}" for name, value in results.items())
        response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT}, {"role": "user", "content": f"Original Task: {task}\n\nResults:\n{packed}"}])
        return response.choices[0].message.content or "No synthesis generated."

    def orchestrate(self, task: str) -> tuple[WorkflowPlan, str]:
        plan = self.plan(task)
        manager_cls = DIVISION_MAP[plan.division]
        manager_brief = self._run_agent(manager_cls, f"GENERAL MANAGER ASSIGNMENT:\n{task}\nSpecialists selected: {', '.join(plan.specialists)}\nCoordinate this division; do not claim unconfirmed execution.")
        results: dict[str, str] = {f"{plan.division}_manager": manager_brief}
        context = f"Original task:\n{task}\n\nDivision manager brief:\n{manager_brief}"
        for name in plan.specialists:
            if plan.division == "business" and name == "travel" and self._is_calendar_read(task):
                output = self._calendar_read(task)
            else:
                output = self._run_agent(DIVISION_SPECIALISTS[plan.division][name], context)
            results[name] = output
            context += f"\n\n{name.upper()} OUTPUT:\n{output}"
        return plan, self.synthesize(task, results)

    def run(self, task: str) -> str:
        return self.orchestrate(task)[1]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="General manager for hierarchical autonomous AI agent team.")
    parser.add_argument("task", type=str)
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    parser.add_argument("--agent-model", type=str, default=None)
    return parser.parse_args()

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    args = parse_args()
    print("\n=== FINAL ANSWER ===")
    print(Orchestrator(model=args.model, agent_model=args.agent_model).run(args.task))

if __name__ == "__main__":
    main()
