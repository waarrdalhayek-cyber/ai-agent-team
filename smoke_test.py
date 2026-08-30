"""Smoke tests for the hierarchical autonomous AI agent team."""
from __future__ import annotations
import unittest
from orchestrator import Orchestrator

class FakeMessage:
    def __init__(self, content: str) -> None: self.content = content
class FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = FakeMessage(content); self.finish_reason = "stop"
class FakeResponse:
    def __init__(self, content: str) -> None: self.choices = [FakeChoice(content)]
class FakeCompletions:
    def __init__(self, scripted_responses: list[str]) -> None:
        self._responses = list(scripted_responses); self.calls: list[dict[str, object]] = []
    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses: raise AssertionError("No fake responses remaining.")
        return FakeResponse(self._responses.pop(0))
class FakeChat:
    def __init__(self, scripted_responses: list[str]) -> None: self.completions = FakeCompletions(scripted_responses)
class FakeOpenAIClient:
    def __init__(self, scripted_responses: list[str]) -> None: self.chat = FakeChat(scripted_responses)

class OrchestratorSmokeTests(unittest.TestCase):
    def test_business_request_goes_through_business_manager_then_ecommerce(self) -> None:
        client = FakeOpenAIClient([
            '{"division":"business","specialists":["ecommerce"],"reason":"E-commerce request."}',
            "Business manager brief",
            "Ecommerce analysis",
            "Final synthesized answer",
        ])
        orchestrator = Orchestrator(client=client)
        plan, result = orchestrator.orchestrate("Analyze a viral product and prepare a store plan without spending money.")
        self.assertEqual(plan.division, "business")
        self.assertEqual(plan.specialists, ["ecommerce"])
        self.assertEqual(result, "Final synthesized answer")
        ecommerce_call = client.chat.completions.calls[2]
        self.assertIn("Business manager brief", ecommerce_call["messages"][1]["content"])

    def test_learning_request_goes_through_creative_learning_manager(self) -> None:
        client = FakeOpenAIClient([
            '{"division":"creative_learning","specialists":["learning"],"reason":"Tutoring request."}',
            "Learning division brief",
            "Lesson output",
            "Learning final answer",
        ])
        orchestrator = Orchestrator(client=client)
        plan, result = orchestrator.orchestrate("Teach me mental arithmetic.")
        self.assertEqual(plan.division, "creative_learning")
        self.assertEqual(plan.specialists, ["learning"])
        self.assertEqual(result, "Learning final answer")

    def test_single_agent_route_still_works(self) -> None:
        client = FakeOpenAIClient(["Execution only"])
        orchestrator = Orchestrator(client=client)
        self.assertEqual(orchestrator.route("Plan a deployment", "execution"), "Execution only")

if __name__ == "__main__": unittest.main(verbosity=2)
