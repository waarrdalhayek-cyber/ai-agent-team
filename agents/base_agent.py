"""Base agent class shared by all specialized agents."""

import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents in the team."""

    def __init__(self, name: str, system_prompt: str, model: str = "gpt-4o-mini"):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
        self.client = OpenAI(api_key=api_key)

    def run(self, task: str) -> str:
        """Send a task to the agent and return its response."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": task},
                ],
            )
        except Exception as exc:
            logger.exception("OpenAI call failed for %s", self.name)
            raise RuntimeError(f"{self.name} failed while calling OpenAI API: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            finish_reason = response.choices[0].finish_reason
            raise RuntimeError(
                f"{self.name} received a response with no text content "
                f"(finish_reason={finish_reason!r})."
            )

        return content
