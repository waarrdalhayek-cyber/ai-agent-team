# AI Agent Team

An autonomous AI agent team built with Python and the OpenAI API.

## What it does

- Keeps the existing orchestrator and specialized agents.
- Uses the OpenAI API to choose the best agent workflow automatically.
- Supports sequential collaboration across `research`, `content`, and `execution`.
- Reads the API key only from the `OPENAI_API_KEY` environment variable.
- Includes logging, error handling, and a smoke test.

## Architecture

```text
orchestrator.py          ← CLI entrypoint and OpenAI-backed workflow orchestrator
agents/
  base_agent.py          ← shared OpenAI client, task execution, collaboration context
  research_agent.py      ← gathers and summarises information
  content_agent.py       ← drafts and refines written content
  execution_agent.py     ← produces concrete action plans and final actionable output
smoke_test.py            ← local smoke test with a fake OpenAI client
```

The design remains modular. To add another specialist:
1. Create a new file in `agents/` that subclasses `BaseAgent`.
2. Export the class from `agents/__init__.py`.
3. Register it in `AGENT_MAP` inside `/home/runner/work/ai-agent-team/ai-agent-team/orchestrator.py`.

## Requirements

- Python 3.9+
- An [OpenAI API key](https://platform.openai.com/account/api-keys)

## Setup

```bash
cd /home/runner/work/ai-agent-team/ai-agent-team

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

export OPENAI_API_KEY="sk-your-real-key"
```

## Run the agent team

```bash
cd /home/runner/work/ai-agent-team/ai-agent-team
source .venv/bin/activate

# Let the orchestrator choose the workflow automatically
python orchestrator.py "Research the latest AI coding agent trends and turn them into a launch plan"

# Force a single specialist when needed
python orchestrator.py --agent research "Summarize the latest developments in battery technology"
python orchestrator.py --agent content "Write a short launch announcement for a new AI product"
python orchestrator.py --agent execution "Create a rollout checklist for a small Python service"
```

## CLI options

```bash
python orchestrator.py --help
python orchestrator.py --log-level DEBUG "Your task here"
python orchestrator.py --model gpt-4o-mini "Your task here"
```

## Smoke test

The smoke test does not call the real OpenAI API. It uses a fake client to verify routing, sequential collaboration, and final synthesis.

```bash
cd /home/runner/work/ai-agent-team/ai-agent-team
source .venv/bin/activate

python smoke_test.py
```

## Environment variable

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key used by the orchestrator and all agents |

## Security

- Never hard-code API keys or secrets in source files, tests, or documentation.
- The application reads credentials from `OPENAI_API_KEY` at runtime.
- Keep the key in your shell environment or another secure secret manager.
