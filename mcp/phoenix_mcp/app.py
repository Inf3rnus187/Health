"""The FastMCP instance every tool module registers on."""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

INSTRUCTIONS = """Phoenix Health Hub: a personal medical hub (French UI).
It holds Apple Health data (full export + daily Health Auto Export), lab
results and FibroScan read from PDFs, the medical record (documents,
conditions, treatments, appointments), progress photos and reports.
Start with health_summary, medical_record and data_inventory. Metric keys
are canonical (body.weight, bio.hba1c, liver.cap…): use list_metrics /
metric_overview. Values from documents are verified against the text;
AI summaries are not diagnoses. Answer the user in French."""

mcp = FastMCP(
    "phoenix-health-hub",
    instructions=INSTRUCTIONS,
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_PORT", "9000")),
    # streamable-http: every request is answered on its own (plain JSON,
    # no session), so a single curl can call a tool.
    stateless_http=True,
    json_response=True,
)
