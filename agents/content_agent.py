"""Content creation agent — drafts and refines written content."""

from typing import Any

from .base_agent import BaseAgent

SYSTEM_PROMPT = (
    "You are a content creation specialist. Your role is to draft, edit, and refine "
    "written content including articles, reports, summaries, and marketing copy. "
    "Adapt your tone and style to the requirements provided and aim for clarity, "
    "engagement, and correctness. If prior agent context is provided, use it to improve "
    "the final writing without discarding useful information."
)


class ContentAgent(BaseAgent):
    """Specialised agent for content creation and writing."""

    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None):
        super().__init__(
            name="ContentAgent",
            system_prompt=SYSTEM_PROMPT,
            model=model,
            client=client,
        )
