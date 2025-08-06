## Introduction
This repo contains the steps to configure MCP based Claude Desktop to get insights on cricket data stored in postgres db with natural language queries. Follow the below instructions

### 1  Prerequisites
- Python (3.10 or newer recommended)
- PostgreSQL (local or remote instance)
- Claude Desktop installed
- OpenAI / Anthropic API Key with active quota

### 2  Installation Steps

### 2·1  Clone & Create a virtual environment

```bash
git clone https://github.com/tejaswininakirekanti/cricket_db_mcp.git cricket‑mcp
cd cricket‑mcp
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2·2  Install dependencies

```bash
pip install -r requirements.txt
```

### 2·3  Set environment variables

Create a file called **.env** in the project root:

```env
# Postgres – use ANY user with SELECT rights; read‑only is safer and update password
PG_DSN=postgresql+psycopg://<user>:<pwd>@127.0.0.1:5432/cricket_stats

# Choose ONE provider ↓
OPENAI_API_KEY=sk‑…            # OR
# ANTHROPIC_API_KEY=sk‑ant‑…
```

### 2·4  Load the sample cricket data

```bash
psql -U admin -d cricket_stats -f extras/create_schema.sql   # to create schema
python extras/load_data.py     # to populate data
```

### 2·5  Run the MCP server (local dev)

```bash
python cricket_mcp.py               # uses STDIO transport by default
```
---

## 3  Integrate to Claude Desktop

1. Open `claude_desktop_config.json` 
2. Append (or edit) the **mcpServers** section:

```jsonc
{
  "mcpServers": {
    "cricket-db": {
      "command": "${PROJECT_ROOT}/.venv/bin/python",  
      "args": ["${PROJECT_ROOT}/cricket_mcp.py"],
      "enabled": true
    }
  }
}
```

3. Restart Claude Desktop. You should see a tool option → **ask\_cricket** tool.

---

## 4  Test Queries

Paste any of these into Claude – it will auto‑invoke the tool and wait until it generate the results.

| Category                | Example Question                                               |
| ----------------------- | -------------------------------------------------------------- |
| **Basic Match Information**          | *Show me all matches in the dataset* <br> *Which team won the most matches* <br> *What was the highest total score*|
| **Player Performance**     | *Who scored the most runs across all matches*  <br> *Which bowler took the most wickets*                |
| **Advanced Analytics**  |*What's the average first innings score?* <br> *Which venue has the highest scoring matches?* <br> *Which team has the best powerplay performance?"* |
| **Match-Specific Queries** | *What was the winning margin in the closest match?* <br> *Show partnerships over 100 runs* |

 
