"""MCP storefront boundary for Catalogsmith."""

from agent.mcp.client import StorefrontMCPClient, get_storefront_client
from agent.mcp.tools import TOOL_NAMES, dispatch_tool

__all__ = [
    "StorefrontMCPClient",
    "TOOL_NAMES",
    "dispatch_tool",
    "get_storefront_client",
]
