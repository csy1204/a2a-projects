"""Phoenix server launcher for observability.

Run with: uv run python -m observability
Or use the script: uv run phoenix-server
"""

import phoenix as px


def main():
    """Launch Phoenix server for LLM observability."""
    print("Starting Phoenix observability server...")
    print("Dashboard will be available at: http://localhost:6006")
    print("Press Ctrl+C to stop the server")

    # Launch Phoenix with default settings
    # This starts a local server with a web UI for viewing traces
    px.launch_app()


if __name__ == "__main__":
    main()
