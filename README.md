# AI Agent Team

An autonomous AI agent team built with Python and the OpenAI API.

## Architecture

```
orchestrator.py          ← CLI entrypoint and autonomous orchestrator
agents/
  base_agent.py          ← shared OpenAI client, secure key loading, API call handling
  research_agent.py      ← gathers and summarises information
  content_agent.py       ← drafts and refines written content
  execution_agent.py     ← plans and describes concrete action steps
smoke_test.py            ← lightweight end-to-end collaboration smoke test
```

The architecture remains modular and extensible:
1. Create a new agent class in `agents/` that subclasses `BaseAgent`.
2. Export it from `agents/__init__.py`.
3. Register it in `AGENT_MAP` in `orchestrator.py`.

## Requirements

- Python 3.9+
- OpenAI API key

## Setup

```bash
# 1) Clone and enter repository
git clone https://github.com/waarrdalhayek-cyber/ai-agent-team.git
cd ai-agent-team

# 2) Create and activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Configure OpenAI API key securely (never hard-code secrets)
export OPENAI_API_KEY="sk-..."      # macOS/Linux
# PowerShell: $env:OPENAI_API_KEY="sk-..."

# Optional convenience (.env is git-ignored)
echo 'OPENAI_API_KEY=sk-...' > .env
```

## Run the autonomous orchestrator

Give exactly one task; the orchestrator automatically selects one or more specialized agents and runs them sequentially when needed.

```bash
python orchestrator.py "Research the best launch strategy, write a concise launch brief, and provide execution steps"
```

Optional flags:

```bash
# Force one specific agent
python orchestrator.py "Write a short product update" --agent content

# Choose model and log level
python orchestrator.py "Plan AWS deployment steps" --model gpt-4o-mini --log-level DEBUG
```

## Smoke test

This smoke test validates routing + sequential collaboration behavior without calling the OpenAI API.

```bash
python smoke_test.py
```

Expected output:

```text
Smoke test passed.
```

## Environment Variables

| Variable         | Required | Description         |
|------------------|----------|---------------------|
| `OPENAI_API_KEY` | ✅ Yes   | OpenAI API key      |

## Security

- Never hard-code API keys or secrets.
- Use `OPENAI_API_KEY` from your environment or a local `.env` file.
- `.env` is already git-ignored in this repository.
