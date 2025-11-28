"""Weather Agent Executor - A2A Protocol bridge."""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

from .agent import WeatherAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherAgentExecutor(AgentExecutor):
    """Weather Agent Executor - bridges A2A protocol with WeatherAgent."""

    def __init__(self):
        self.agent = WeatherAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the weather agent for the given request context.

        Args:
            context: The request context containing user input and task info.
            event_queue: Queue for sending task updates to the client.
        """
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        task = context.current_task

        if not task:
            task = new_task(context.message)  # type: ignore
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            async for item in self.agent.stream(query, task.context_id):
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']

                if not is_task_complete and not require_user_input:
                    # Intermediate status update (working state)
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item['content'],
                            task.context_id,
                            task.id,
                        ),
                    )
                elif require_user_input:
                    # Need more input from user
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item['content'],
                            task.context_id,
                            task.id,
                        ),
                        final=True,
                    )
                    break
                else:
                    # Task completed successfully
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='weather_result',
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        """Validate the incoming request.

        Args:
            context: The request context to validate.

        Returns:
            True if validation fails, False if valid.
        """
        # Basic validation - can be extended as needed
        return False

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel the current task execution.

        Args:
            context: The request context.
            event_queue: The event queue.

        Raises:
            ServerError: Cancellation is not supported.
        """
        raise ServerError(error=UnsupportedOperationError())
