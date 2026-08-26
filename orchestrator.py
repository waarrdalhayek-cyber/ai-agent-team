"""Orchestrator — routes tasks to specialised agents and collects results."""

import os
import sys

from dotenv import load_dotenv

from agents import ContentAgent, ExecutionAgent, ResearchAgent

# Load .env file if present (optional convenience; OPENAI_API_KEY can also be
# exported directly in the shell).
load_dotenv()

AGENT_MAP = {
    "research": ResearchAgent,
    "content": ContentAgent,
    "execution": ExecutionAgent,
}

# Reserved for a future LLM-based router that will replace the keyword
# heuristics in orchestrate() below.
ORCHESTRATOR_SYSTEM = (
    "You are an AI orchestrator managing a team of specialised agents: "
    "a ResearchAgent, a ContentAgent, and an ExecutionAgent. "
    "Your job is to analyse user requests, delegate work to the appropriate agent, "
    "and synthesise the results into a coherent final answer."
)


def route(task: str, agent_type: str) -> str:
    """Instantiate the requested agent and run the task."""
    AgentClass = AGENT_MAP.get(agent_type)
    if AgentClass is None:
        raise ValueError(
            f"Unknown agent type '{agent_type}'. "
            f"Choose from: {', '.join(AGENT_MAP.keys())}"
        )
    agent = AgentClass()
    print(f"\n[Orchestrator] Delegating to {AgentClass.__name__}…")
    result = agent.run(task)
    print(f"[{AgentClass.__name__}] Done.\n")
    return result


def orchestrate(task: str) -> str:
    """
    Simple heuristic routing: pick the best agent based on keywords in the task.
    For a production system, replace this with an LLM-based router.
    """
    task_lower = task.lower()
    if any(kw in task_lower for kw in ("research", "find", "search", "analyse", "analyze", "summarise", "summarize", "information about")):
        agent_type = "research"
    elif any(kw in task_lower for kw in ("write", "draft", "create content", "article", "blog", "report", "copy")):
        agent_type = "content"
    else:
        agent_type = "execution"

    return route(task, agent_type)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py \"<your task>\" [agent_type]")
        print(f"       agent_type is optional. Choices: {', '.join(AGENT_MAP.keys())}")
        sys.exit(1)

    task = sys.argv[1]
    agent_type = sys.argv[2] if len(sys.argv) >= 3 else None

    if agent_type:
        result = route(task, agent_type)
    else:
        result = orchestrate(task)

    print("=== Result ===")
    print(result)


if __name__ == "__main__":
    main()
