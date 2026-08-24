# poc-bug-with-ai

> **"Com MCP" PoC** — A QA engineer describes a bug in plain language; the AI agent autonomously opens a Jira issue.

```
QA → python main.py "..." → Agno Agent (Gemini) → Jira MCP Server → Bug aberto ✓
```

---

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure credentials

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Gemini API key — [get one here](https://aistudio.google.com/app/apikey) |
| `JIRA_URL` | Your Atlassian instance URL, e.g. `https://acme.atlassian.net` |
| `JIRA_EMAIL` | Email linked to your Atlassian account |
| `JIRA_API_TOKEN` | [Generate an API token](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRA_PROJECT_KEY` | Key of the project where bugs will be created (e.g. `PROJ`) |

---

## Usage

### Single-shot (recommended for scripting)

```bash
python main.py "Login button crashes on Safari iOS 17 after 3 rapid taps"
```

### Interactive chat loop

```bash
python main.py
```

```
🤖 Bug Reporter Agent (type 'exit' or Ctrl-C to quit)

You: The checkout page goes blank when the user applies a promo code on Firefox
...
✅ Bug created: PROJ-42
🔗 https://acme.atlassian.net/browse/PROJ-42
```

---

## Architecture

```
main.py  (Agno Agent + Gemini)
  └── MCPTools (stdio)
        └── jira_mcp_server.py  (FastMCP)
              ├── get_project_info()
              ├── search_issues()      ← duplicate check
              └── create_issue()       ← opens the bug
```

### Agent workflow

1. QA provides a plain-language bug description.
2. Agent calls `search_issues` to look for duplicates.
3. If none found, agent calls `create_issue` with a structured report.
4. Agent prints the Jira issue key and URL.

---

## Project structure

```
poc-bug-with-ai/
├── main.py               # Agno agent entry point
├── jira_mcp_server.py    # FastMCP Jira tools server
├── pyproject.toml        # Python project & dependencies
├── .env.example          # Environment variable template
├── .env                  # Your credentials (gitignored)
└── README.md
```
