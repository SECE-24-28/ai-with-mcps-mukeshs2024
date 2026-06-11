"""MCP Server — Analyst"""

from mcp.server.fastmcp import FastMCP
from multi_agent_pipeline.tools.analyst import analyze_data

mcp = FastMCP("analyst-server")
mcp.tool()(analyze_data)

if __name__ == "__main__":
    mcp.run(transport="stdio")
