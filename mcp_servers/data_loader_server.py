"""MCP Server — Data Loader"""

from mcp.server.fastmcp import FastMCP
from multi_agent_pipeline.tools.data_loader import load_csv_file, get_data_preview

mcp = FastMCP("data-loader-server")
mcp.tool()(load_csv_file)
mcp.tool()(get_data_preview)

if __name__ == "__main__":
    mcp.run(transport="stdio")
