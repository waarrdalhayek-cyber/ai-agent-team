# AI Agent Team

An autonomous AI agent team built with Python and the OpenAI API.

## Architecture

```
orchestrator.py          ← entry point; routes tasks to the right agent
agents/
  base_agent.py          ← shared OpenAI client & run() logic
  research_agent.py      ← gathers and summarises information
  content_agent.py       ← drafts and refines written content
  execution_agent.py     ← plans and describes concrete action steps
```

The design is intentionally modular. New agents can be added by:
1. Creating a new file in `agents/` that subclasses `BaseAgent`.
2. Exporting the new class from `agents/__init__.py`.
3. Registering it in `AGENT_MAP` inside `orchestrator.py`.

## Requirements

- Python 3.9+
- An [OpenAI API key](https://platform.openai.com/account/api-keys)

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/waarrdalhayek-cyber/ai-agent-team.git
cd ai-agent-team

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your OpenAI API key
#    Option A – export it in your shell (never hard-code it)
export OPENAI_API_KEY="sk-..."

#    Option B – create a .env file (git-ignored)
echo 'OPENAI_API_KEY=sk-...' > .env
```

## Running

```bash
# Let the orchestrator pick the best agent automatically
python orchestrator.py "Research the latest advances in quantum computing"

# Or explicitly choose an agent (research | content | execution)
python orchestrator.py "Write a blog post about renewable energy" content
python orchestrator.py "Plan the steps to deploy a web app to AWS" execution
```

## Environment Variables

| Variable         | Required | Description                    |
|------------------|----------|--------------------------------|
| `OPENAI_API_KEY` | ✅ Yes   | Your OpenAI API key            |

## Security

- **Never** hard-code API keys or other secrets in source files.
- Add `.env` to your `.gitignore` if you use one locally.
