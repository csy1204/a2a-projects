"""Weather Agent Server - Entry point for A2A server."""

import logging
import os
import sys

import click
import httpx
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv

from observability import init_tracing

from .agent import WeatherAgent
from .agent_executor import WeatherAgentExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost', help='Server host')
@click.option('--port', 'port', default=10000, help='Server port')
def main(host: str, port: int):
    """Starts the Weather Agent server."""
    try:
        # Validate API keys
        if os.getenv('model_source', 'google') == 'google':
            if not os.getenv('GOOGLE_API_KEY'):
                raise MissingAPIKeyError(
                    'GOOGLE_API_KEY environment variable not set.'
                )
        else:
            if not os.getenv('TOOL_LLM_URL'):
                raise MissingAPIKeyError(
                    'TOOL_LLM_URL environment variable not set.'
                )
            if not os.getenv('TOOL_LLM_NAME'):
                raise MissingAPIKeyError(
                    'TOOL_LLM_NAME environment variable not set.'
                )

        if not os.getenv('OPENWEATHER_API_KEY'):
            raise MissingAPIKeyError(
                'OPENWEATHER_API_KEY environment variable not set.'
            )

        # Initialize Phoenix tracing for observability
        init_tracing(project_name='weather-agent')

        # Define agent capabilities
        capabilities = AgentCapabilities(streaming=True, push_notifications=True)

        # Define agent skills
        skill_weather = AgentSkill(
            id='get_weather',
            name='Weather Lookup Tool',
            description='Get current weather and forecasts for any city worldwide',
            tags=['weather', 'forecast', 'temperature', 'climate'],
            examples=[
                'What is the weather in Seoul?',
                'Give me a 5-day forecast for Tokyo',
                'How hot is it in New York right now?',
            ],
        )

        skill_history = AgentSkill(
            id='weather_history',
            name='Weather History Tool',
            description='Query previously searched weather data',
            tags=['weather', 'history', 'search'],
            examples=[
                'Show my recent weather searches',
                'What cities have I searched for?',
            ],
        )

        # Create agent card
        agent_card = AgentCard(
            name='Weather Agent',
            description='A specialized assistant for weather information. '
                        'Get current weather, forecasts, and maintain search history.',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            default_input_modes=WeatherAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=WeatherAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill_weather, skill_history],
        )

        # Set up A2A infrastructure
        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(
            httpx_client=httpx_client,
            config_store=push_config_store,
        )

        request_handler = DefaultRequestHandler(
            agent_executor=WeatherAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config_store,
            push_sender=push_sender,
        )

        server = A2AFastAPIApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )

        # Build app and add CORS middleware
        app = server.build()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

        logger.info(f'Starting Weather Agent server at http://{host}:{port}')
        uvicorn.run(app, host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
