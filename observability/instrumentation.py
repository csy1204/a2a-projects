"""LangChain instrumentation for Phoenix tracing.

This module provides functions to initialize Phoenix tracing
for LangChain/LangGraph applications with custom decorators.
"""

import functools
import json
import os
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Type variable for preserving function signatures
F = TypeVar("F", bound=Callable[..., Any])

# Global tracer instance
_tracer: trace.Tracer | None = None


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer("a2a-weather-agent")
    return _tracer


def init_tracing(
    project_name: str = "a2a-weather-agent",
    endpoint: str | None = None,
) -> None:
    """Initialize Phoenix tracing for LangChain.

    Call this function at the start of your application to enable
    automatic tracing of all LangChain/LangGraph operations.

    Args:
        project_name: Name of the project in Phoenix dashboard.
        endpoint: Phoenix collector endpoint. Defaults to local Phoenix server.
    """
    import phoenix as px
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from phoenix.otel import register

    # Use environment variable or default to local Phoenix
    collector_endpoint = endpoint or os.getenv(
        "PHOENIX_COLLECTOR_ENDPOINT",
        "http://localhost:6006/v1/traces"
    )

    # Register Phoenix tracer provider
    tracer_provider = register(
        project_name=project_name,
        endpoint=collector_endpoint,
    )

    # Instrument LangChain - this captures LLM calls (ChatOpenAI, etc.)
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

    # Set up our custom tracer
    global _tracer
    _tracer = trace.get_tracer("a2a-weather-agent", tracer_provider=tracer_provider)

    print(f"Phoenix tracing initialized for project: {project_name}")
    print(f"Sending traces to: {collector_endpoint}")


def _serialize_value(value: Any) -> str:
    """Serialize a value to string for span attributes."""
    try:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return str(value)
    except Exception:
        return str(value)


def trace_tool(
    name: str | None = None,
    capture_input: bool = True,
    capture_output: bool = True,
) -> Callable[[F], F]:
    """Decorator to trace tool execution with input/output capture.

    Use this decorator on tool functions to create spans in Phoenix
    that capture the function's input arguments and return value.

    Args:
        name: Custom span name. Defaults to function name.
        capture_input: Whether to capture input arguments. Defaults to True.
        capture_output: Whether to capture return value. Defaults to True.

    Returns:
        Decorated function with tracing.

    Example:
        @trace_tool(name="get_weather")
        @tool
        def get_current_weather(city: str) -> dict:
            ...
    """
    def decorator(func: F) -> F:
        span_name = name or f"tool.{func.__name__}"

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()

            with tracer.start_as_current_span(span_name) as span:
                # Set span kind and attributes
                span.set_attribute("tool.name", func.__name__)
                span.set_attribute("tool.type", "sync")

                # Capture input
                if capture_input:
                    if args:
                        span.set_attribute("input.args", _serialize_value(args))
                    if kwargs:
                        span.set_attribute("input.kwargs", _serialize_value(kwargs))

                try:
                    result = func(*args, **kwargs)

                    # Capture output
                    if capture_output and result is not None:
                        span.set_attribute("output.result", _serialize_value(result))

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()

            with tracer.start_as_current_span(span_name) as span:
                # Set span kind and attributes
                span.set_attribute("tool.name", func.__name__)
                span.set_attribute("tool.type", "async")

                # Capture input
                if capture_input:
                    if args:
                        span.set_attribute("input.args", _serialize_value(args))
                    if kwargs:
                        span.set_attribute("input.kwargs", _serialize_value(kwargs))

                try:
                    result = await func(*args, **kwargs)

                    # Capture output
                    if capture_output and result is not None:
                        span.set_attribute("output.result", _serialize_value(result))

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def trace_span(name: str) -> Callable[[F], F]:
    """Simple decorator to create a named span around a function.

    Use this for general functions that aren't tools but should be traced.

    Args:
        name: Span name.

    Returns:
        Decorated function with tracing.

    Example:
        @trace_span("process_request")
        def process_request(data: dict) -> dict:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                span.set_attribute("function.name", func.__name__)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                span.set_attribute("function.name", func.__name__)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def init_tracing_with_local_phoenix(
    project_name: str = "a2a-weather-agent",
) -> None:
    """Initialize tracing with an embedded Phoenix instance.

    This launches Phoenix in the background and configures tracing.
    Useful for development when you don't want to run Phoenix separately.

    Args:
        project_name: Name of the project in Phoenix dashboard.
    """
    import phoenix as px

    # Launch Phoenix in background
    session = px.launch_app()
    print(f"Phoenix UI available at: {session.url}")

    # Initialize tracing to the embedded Phoenix
    init_tracing(
        project_name=project_name,
        endpoint=f"{session.url}v1/traces",
    )
