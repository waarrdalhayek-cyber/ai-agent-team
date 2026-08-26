"""Research agent — gathers and summarises information."""

from typing import Any

from .base_agent import BaseAgent

SYSTEM_PROMPT = (
    "You are a research specialist. Your role is to gather, analyse, and summarise "
    "information on any topic the user provides. Present findings clearly and concisely, "
    "with key points highlighted. Always cite your reasoning and flag uncertainties. "
    "If prior agent context is provided, validate it and build on it."
)


class ResearchAgent(BaseAgent):
    """Specialised agent for research and information gathering."""

    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None):
        super().__init__(
            name="ResearchAgent",
            system_prompt=SYSTEM_PROMPT,
            model=model,
            client=client,
        )
