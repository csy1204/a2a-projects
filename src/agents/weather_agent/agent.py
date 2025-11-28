"""Weather Agent - LangGraph ReAct Agent for weather information.

LangGraph 1.0+ / LangChain 1.1+ compatible.
"""

import os
from collections.abc import AsyncIterable
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from langchain.agents.structured_output import AutoStrategy
from pydantic import BaseModel, Field

from src.tools.api_tools.weather_api.weather_api import (
    get_current_weather,
    get_weather_forecast,
)
from src.tools.data_tools.weather_db.weather_db import (
    get_weather_history,
    save_weather_query,
)


class WeatherResponseFormat(BaseModel):
    """Structured response format for the weather agent."""

    status: Literal['input_required', 'completed', 'error'] = Field(
        default='input_required',
        description='The status of the response',
    )
    message: str = Field(
        description='The response message to the user',
    )


class WeatherAgent:
    """WeatherAgent - a specialized assistant for weather information.

    Uses LangGraph's ReAct agent pattern with structured output.
    Compatible with LangGraph 1.0+ and LangChain 1.1+.
    """

    SYSTEM_INSTRUCTION = (
        'You are a specialized weather assistant. '
        'Your purpose is to provide weather information using the available tools. '
        '\n\n'
        'Available capabilities:\n'
        '1. Get current weather for any city using get_current_weather\n'
        '2. Get 5-day weather forecast using get_weather_forecast\n'
        '3. Save weather queries to history using save_weather_query\n'
        '4. Retrieve previous weather queries using get_weather_history\n'
        '\n'
        'When providing weather information:\n'
        '- Always include temperature, weather description, and humidity\n'
        '- Mention the temperature unit (Celsius or Fahrenheit)\n'
        '- For forecasts, summarize the key weather changes\n'
        '- Save important queries to history for user reference\n'
        '\n'
        'If the user asks about anything other than weather, '
        'politely state that you can only assist with weather-related queries.'
    )

    FORMAT_INSTRUCTION = (
        'Set response status to input_required if the user needs to provide more information '
        '(e.g., city name is missing or ambiguous). '
        'Set response status to error if there is an error while processing the request. '
        'Set response status to completed if the weather information request is fully answered.'
    )

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        """Initialize the WeatherAgent with LLM and tools."""
        model_source = os.getenv('model_source', 'google')

        if model_source == 'google':
            self.model = ChatGoogleGenerativeAI(
                model=os.getenv('GOOGLE_MODEL_NAME', 'gemini-2.0-flash'),
                temperature=0,
            )
        else:
            self.model = ChatOpenAI(
                model=os.getenv('TOOL_LLM_NAME', 'gpt-4'),
                api_key=os.getenv('API_KEY', 'EMPTY'),
                base_url=os.getenv('TOOL_LLM_URL'),
                temperature=0,
            )

        self.tools = [
            get_current_weather,
            get_weather_forecast,
            save_weather_query,
            get_weather_history,
        ]

        # Create memory saver for conversation state persistence
        self.memory = MemorySaver()

        # Create ReAct agent with LangGraph 1.0+ API
        self.graph = create_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.memory,
            system_prompt=self.SYSTEM_INSTRUCTION,
            response_format=AutoStrategy(
                WeatherResponseFormat
            ),  # (self.FORMAT_INSTRUCTION, WeatherResponseFormat),
        )

    async def stream(self, query: str, context_id: str) -> AsyncIterable[dict[str, Any]]:
        """Stream responses from the agent.

        Uses LangGraph's async streaming for better performance.

        Args:
            query: User's query string.
            context_id: Context/thread ID for conversation state.

        Yields:
            Dictionary containing task state and content.
        """
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        # Use async streaming (astream) for LangGraph 1.0+
        async for item in self.graph.astream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]

            if isinstance(message, AIMessage) and message.tool_calls:
                tool_name = message.tool_calls[0].get('name', 'tool')
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': f'Looking up weather information ({tool_name})...',
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing weather data...',
                }

        yield await self._get_agent_response(config)

    async def _get_agent_response(self, config: dict) -> dict[str, Any]:
        """Get the final structured response from the agent.

        Args:
            config: LangGraph configuration dictionary.

        Returns:
            Dictionary containing task completion state and response content.
        """
        # Use async get_state for LangGraph 1.0+
        current_state = await self.graph.aget_state(config)
        structured_response = current_state.values.get('structured_response')

        if structured_response and isinstance(structured_response, WeatherResponseFormat):
            if structured_response.status == 'input_required':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                'Unable to process your weather request at the moment. '
                'Please try again.'
            ),
        }

    def get_agent_response(self, config: dict) -> dict[str, Any]:
        """Get the final structured response (sync version).

        Args:
            config: LangGraph configuration dictionary.

        Returns:
            Dictionary containing task completion state and response content.
        """
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')

        if structured_response and isinstance(
            structured_response, WeatherResponseFormat
        ):
            if structured_response.status == 'input_required':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                'Unable to process your weather request at the moment. '
                'Please try again.'
            ),
        }
