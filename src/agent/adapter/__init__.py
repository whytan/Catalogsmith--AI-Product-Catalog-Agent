"""Storefront adapter — sole boundary for catalog reads and writes."""

from agent.adapter.protocol import StorefrontAdapter
from agent.adapter.sqlite import SQLiteStorefrontAdapter, adapter_for

__all__ = ["StorefrontAdapter", "SQLiteStorefrontAdapter", "adapter_for"]
