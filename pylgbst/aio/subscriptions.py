"""
Delivery of decoded peripheral values to subscribers, off the message dispatch path
"""
import asyncio
import inspect
import logging
from typing import Callable, Optional, Tuple

log = logging.getLogger(__name__)

_CLOSED = object()


class Subscription:
    """
    Values for one subscriber. Sensor readings keep only the latest value: a slow consumer
    sees the current state, not a backlog. Events (button presses) keep every value.
    """

    def __init__(self, keep_all: bool):
        self._keep_all = keep_all
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None

    def push(self, values: Tuple) -> None:
        if not self._keep_all:
            while not self._queue.empty():
                self._queue.get_nowait()
        self._queue.put_nowait(values)

    def close(self) -> None:
        self._queue.put_nowait(_CLOSED)

    def __aiter__(self):
        return self

    async def __anext__(self) -> Tuple:
        values = await self._queue.get()
        if values is _CLOSED:
            raise StopAsyncIteration
        return values

    def deliver_to(self, callback: Callable) -> None:
        """Call `callback(*values)` for each value, in a task of its own; coroutine functions are awaited"""
        self._task = asyncio.create_task(self._deliver(callback), name="subscription %r" % callback)

    async def _deliver(self, callback: Callable) -> None:
        async for values in self:
            try:
                result = callback(*values)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                log.exception("Subscriber %r failed on %r", callback, values)
