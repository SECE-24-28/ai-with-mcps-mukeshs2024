"""MCP Server — Data Cleaner"""

from mcp.server.fastmcp import FastMCP
from multi_agent_pipeline.tools.data_cleaner import clean_data

mcp = FastMCP("data-cleaner-server")
mcp.tool()(clean_data)

if __name__ == "__main__":
    mcp.run(transport="stdio")
