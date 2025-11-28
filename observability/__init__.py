"""Observability module for A2A Projects.

Uses Arize Phoenix for LLM observability and tracing.
"""

from .instrumentation import init_tracing, trace_tool, trace_span

__all__ = ["init_tracing", "trace_tool", "trace_span"]
