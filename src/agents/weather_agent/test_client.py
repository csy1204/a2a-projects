"""Test client for Weather Agent."""

import logging
from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)


async def main() -> None:
    """Run test scenarios for the Weather Agent."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = 'http://localhost:10000'

    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )

        # Fetch Agent Card
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(f'Fetching agent card from: {base_url}')
            _public_card = await resolver.get_agent_card()
            logger.info('Successfully fetched agent card:')
            logger.info(_public_card.model_dump_json(indent=2, exclude_none=True))
            final_agent_card_to_use = _public_card

        except Exception as e:
            logger.error(f'Failed to fetch agent card: {e}', exc_info=True)
            raise RuntimeError('Failed to fetch agent card.') from e

        # Initialize A2A Client
        client = A2AClient(
            httpx_client=httpx_client,
            agent_card=final_agent_card_to_use,
        )
        logger.info('A2AClient initialized.')

        # Test 1: Current Weather Query
        logger.info('\n' + '=' * 50)
        logger.info('Test 1: Current Weather Query')
        logger.info('=' * 50)

        weather_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'What is the weather in Seoul?'}
                ],
                'message_id': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**weather_payload),
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        # Test 2: Weather Forecast Query
        logger.info('\n' + '=' * 50)
        logger.info('Test 2: Weather Forecast Query')
        logger.info('=' * 50)

        forecast_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Give me a 5-day forecast for Tokyo'}
                ],
                'message_id': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**forecast_payload),
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        # Test 3: Multi-turn Conversation (missing city)
        logger.info('\n' + '=' * 50)
        logger.info('Test 3: Multi-turn Conversation')
        logger.info('=' * 50)

        ambiguous_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'What is the weather?'}
                ],
                'message_id': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**ambiguous_payload),
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        # Continue conversation with city name
        task_id = response.root.result.id
        context_id = response.root.result.context_id

        followup_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'New York'}],
                'message_id': uuid4().hex,
                'task_id': task_id,
                'context_id': context_id,
            },
        }
        followup_request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**followup_payload),
        )

        followup_response = await client.send_message(followup_request)
        print(followup_response.model_dump(mode='json', exclude_none=True))

        # Test 4: Weather History Query
        logger.info('\n' + '=' * 50)
        logger.info('Test 4: Weather History Query')
        logger.info('=' * 50)

        history_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Show my recent weather searches'}
                ],
                'message_id': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**history_payload),
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        # Test 5: Streaming Request
        logger.info('\n' + '=' * 50)
        logger.info('Test 5: Streaming Weather Request')
        logger.info('=' * 50)

        streaming_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'What is the weather in London?'}
                ],
                'message_id': uuid4().hex,
            },
        }
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**streaming_payload),
        )

        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            print(chunk.model_dump(mode='json', exclude_none=True))


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
