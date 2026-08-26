"""Base agent class shared by all specialized agents."""

from __future__ import annotations

import logging
import os
from typing import Any

from openai import OpenAI


class BaseAgent:
    """Base class for all agents in the team."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = "gpt-4o-mini",
        client: Any | None = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.logger = logging.getLogger(name)
        self.client = client or OpenAI(api_key=self._get_api_key())

    @staticmethod
    def _get_api_key() -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY environment variable is not set."
            )
        return api_key

    def _build_user_prompt(self, task: str, collaboration_context: str | None) -> str:
        if not collaboration_context:
            return f"Task:\n{task}"
        return (
            f"Original task:\n{task}\n\n"
            "Context from previous agents:\n"
            f"{collaboration_context}\n\n"
            "Use the prior work where helpful, keep what is correct, and continue the task."
        )

    def run(self, task: str, collaboration_context: str | None = None) -> str:
        """Send a task to the agent and return its response."""
        self.logger.info("Running task")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": self._build_user_prompt(task, collaboration_context),
                    },
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on SDK/runtime details
            self.logger.exception("OpenAI request failed")
            raise RuntimeError(f"{self.name} failed to complete the task: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            finish_reason = response.choices[0].finish_reason
            raise RuntimeError(
                f"{self.name} received a response with no text content "
                f"(finish_reason={finish_reason!r})."
            )

        self.logger.info("Task completed")
        return content.strip()
