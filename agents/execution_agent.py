"""Execution agent — plans and carries out concrete action steps."""

from typing import Any

from .base_agent import BaseAgent

SYSTEM_PROMPT = (
    "You are a task execution specialist. Your role is to take high-level goals and "
    "break them down into concrete, ordered action steps, then simulate or describe "
    "carrying out those steps. Be precise, methodical, and highlight any blockers or "
    "dependencies that need to be resolved before proceeding. If prior agent context is "
    "provided, use it to produce an actionable final answer."
)


class ExecutionAgent(BaseAgent):
    """Specialised agent for task planning and execution."""

    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None):
        super().__init__(
            name="ExecutionAgent",
            system_prompt=SYSTEM_PROMPT,
            model=model,
            client=client,
        )
