import re, os, pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from fastmcp import FastMCP

load_dotenv()

PG_DSN = os.environ["PG_DSN"]

def build_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        return ChatAnthropic(model="claude-3-sonnet-2025-05-17", temperature=0)
    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    raise RuntimeError("Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env")

llm = build_llm()
db  = SQLDatabase.from_uri(PG_DSN)
sql_chain = SQLDatabaseChain.from_llm(
    llm, db, verbose=False, return_intermediate_steps=True
)

SQLQ_RE = re.compile(r"SQLQuery:\s*(.+)", re.I | re.S)
def extract_sql(steps: list) -> str:
    for step in steps:
        if isinstance(step, str):
            m = SQLQ_RE.search(step)
            if m:
                return m.group(1).strip()
        if isinstance(step, dict):
            for key in ("sql_cmd", "input"):
                if key in step and isinstance(step[key], str):
                    m = SQLQ_RE.search(step[key])
                    if m:
                        return m.group(1).strip()
        if isinstance(step, tuple) and isinstance(step[0], str):
            m = SQLQ_RE.search(step[0])
            if m:
                return m.group(1).strip()
    raise ValueError("No SQLQuery found")

def run_sql(sql: str) -> pd.DataFrame:
    eng = create_engine(PG_DSN, pool_pre_ping=True)
    with eng.begin() as conn:
        return pd.read_sql(text(sql), conn)

mcp = FastMCP("cricket")


@mcp.tool()
async def ask_cricket(question: str) -> str:
    resp = sql_chain.invoke({"query": question})
    sql  = extract_sql(resp["intermediate_steps"])

    sql = sql.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1]          # drop the first ```sql line
    if sql.endswith("```"):
        sql = sql.rsplit("\n", 1)[0]         # drop the trailing ``` fence
    df = run_sql(sql)
    if len(df) > 300:
        df = df.head(300)

    return f"**SQL**\n```sql\n{sql}\n```\n\n" + df.to_markdown(index=False)

if __name__ == "__main__":
    mcp.run(transport="stdio")                              # for Claude Desktop
