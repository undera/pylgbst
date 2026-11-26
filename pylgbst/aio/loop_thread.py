"""
An event loop on a daemon thread, so blocking code can drive the async core
"""
import asyncio
import atexit
import logging
import threading
from typing import Coroutine, Optional, TypeVar

T = TypeVar('T')

log = logging.getLogger(__name__)


class LoopThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self.loop.run_forever, name="pylgbst event loop", daemon=True)
        self._thread.start()
        atexit.register(self._stop_at_exit)  # registered first, so it runs after the connections disconnect

    def run(self, coro: Coroutine[object, object, T]) -> T:
        """Run `coro` on the loop and block until it ends; its exception is raised here"""
        if threading.current_thread() is self._thread:
            coro.close()
            raise RuntimeError("Blocking call on the event loop thread would deadlock it: "
                               "message handlers must not call blocking hub methods")
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result()
        except BaseException:
            future.cancel()  # e.g. Ctrl+C: stop the coroutine too
            raise

    def _stop_at_exit(self) -> None:
        async def cancel_tasks():
            tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        try:
            self.run(cancel_tasks())
        except Exception:
            log.exception("Failed to cancel event loop tasks at exit")
        self.loop.call_soon_threadsafe(self.loop.stop)


_shared: Optional[LoopThread] = None
_shared_lock = threading.Lock()


def shared_loop_thread() -> LoopThread:
    """The loop all blocking-API objects of the process share: connections and hubs must live on one loop"""
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = LoopThread()
        return _shared
