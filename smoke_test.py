"""Smoke tests for the autonomous AI agent team."""

from __future__ import annotations

import unittest

from orchestrator import Orchestrator


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = FakeMessage(content)
        self.finish_reason = "stop"


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, scripted_responses: list[str]) -> None:
        self._responses = list(scripted_responses)
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("No fake responses remaining.")
        return FakeResponse(self._responses.pop(0))


class FakeChat:
    def __init__(self, scripted_responses: list[str]) -> None:
        self.completions = FakeCompletions(scripted_responses)


class FakeOpenAIClient:
    def __init__(self, scripted_responses: list[str]) -> None:
        self.chat = FakeChat(scripted_responses)


class OrchestratorSmokeTests(unittest.TestCase):
    def test_multi_agent_workflow_collaborates_sequentially(self) -> None:
        client = FakeOpenAIClient(
            [
                '{"workflow":["execution","research","content"],"reason":"Needs end-to-end help."}',
                "Research findings",
                "Drafted content",
                "Execution plan",
                "Final synthesized answer",
            ]
        )
        orchestrator = Orchestrator(client=client)

        plan, result = orchestrator.orchestrate(
            "Research a topic, write a summary, and propose next actions."
        )

        self.assertEqual(plan.workflow, ["research", "content", "execution"])
        self.assertEqual(result, "Final synthesized answer")

        research_call = client.chat.completions.calls[1]
        content_call = client.chat.completions.calls[2]
        execution_call = client.chat.completions.calls[3]

        self.assertIn("Task:\n", research_call["messages"][1]["content"])
        self.assertIn("RESEARCH OUTPUT:\nResearch findings", content_call["messages"][1]["content"])
        self.assertIn("CONTENT OUTPUT:\nDrafted content", execution_call["messages"][1]["content"])

    def test_single_agent_route_still_works(self) -> None:
        client = FakeOpenAIClient(["Execution only"])
        orchestrator = Orchestrator(client=client)

        result = orchestrator.route("Plan a deployment", "execution")

        self.assertEqual(result, "Execution only")


if __name__ == "__main__":
    unittest.main(verbosity=2)
