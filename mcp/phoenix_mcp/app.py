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
AI summaries are not diagnoses. Answer the user in French.
Work hours: clock_in / clock_out ("j'embauche", "je débauche"), past
logs with import_work_log (dry run first), work_stats for overtime.
Writing: to count something (a bottle of water, a coffee, a cigarette,
a pee) use add_to_counter, which ADDS to the day. record_measurement REPLACES
the day's value: it refuses to erase one unless replace=true, which you
pass only after the user confirmed the new value. Never write
/measurements through api_call. Ask before deleting anything."""

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
