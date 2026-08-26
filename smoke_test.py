"""Smoke test for autonomous routing and sequential collaboration."""

from orchestrator import Orchestrator


class _FakeResearchAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    def run(self, task: str) -> str:
        return "Research findings: users need a 3-step process."


class _FakeContentAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    def run(self, task: str) -> str:
        if "Research findings" not in task:
            raise AssertionError("Content agent did not receive research context.")
        return "Drafted content based on research findings."


class _FakeExecutionAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    def run(self, task: str) -> str:
        if "Drafted content" not in task:
            raise AssertionError("Execution agent did not receive content context.")
        return "Execution plan generated from prior outputs."


def main() -> None:
    orchestrator = Orchestrator(
        agent_map={
            "research": _FakeResearchAgent,
            "content": _FakeContentAgent,
            "execution": _FakeExecutionAgent,
        },
        planner=lambda task: ["research", "content", "execution"],
    )

    result = orchestrator.orchestrate("Research, draft, and execute a launch plan")

    if "Execution plan generated from prior outputs." not in result:
        raise SystemExit("Smoke test failed: missing final execution output.")

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
