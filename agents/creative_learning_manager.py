"""Creative and learning division manager."""
from __future__ import annotations
from typing import Any
from .base_agent import BaseAgent

CREATIVE_LEARNING_SYSTEM_PROMPT = """You are the Creative & Learning Division Manager. Coordinate content, video production, and learning/tutoring work. Route tasks to the appropriate specialist and combine their work without duplication. Preserve the user's curriculum, supplied assets, requested style, and learning goals. Do not claim that media was generated or an external action happened unless a specialist actually confirmed it. Any paid generation or subscription still requires explicit user approval before money is spent."""

class CreativeLearningManager(BaseAgent):
    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None) -> None:
        super().__init__(name="creative_learning_manager", system_prompt=CREATIVE_LEARNING_SYSTEM_PROMPT, model=model, client=client)
