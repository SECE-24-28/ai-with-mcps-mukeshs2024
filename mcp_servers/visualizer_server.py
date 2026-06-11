"""MCP Server — Visualizer"""

from mcp.server.fastmcp import FastMCP
from multi_agent_pipeline.tools.visualizer import create_visualizations

mcp = FastMCP("visualizer-server")
mcp.tool()(create_visualizations)

if __name__ == "__main__":
    mcp.run(transport="stdio")
