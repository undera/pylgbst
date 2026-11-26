"""
Matching the hub's responses to the commands that caused them.

LWP3 has no request ids. What makes matching possible, as observed on a Move Hub:
- the hub responds in the order commands were sent;
- a reply carries enough to identify its request (`DownstreamMsg.is_reply`);
- a Generic Error names only the command type, so it belongs to the oldest
  command of that type still awaiting its first response;
- port output feedback reports per port; on each port, commands progress in
  the order sent: in progress, then completed or discarded.
"""
import asyncio
import logging
from collections import deque
from typing import Deque, Dict, List, Optional

from pylgbst.exceptions import CommandDiscarded, CommandFailed
from pylgbst.messages import DownstreamMsg, MsgGenericError, MsgPortOutput, MsgPortOutputFeedback, UpstreamMsg

log = logging.getLogger(__name__)


class Awaiting:
    """A command waiting for the hub's first response; `acked` resolves with it"""

    def __init__(self, msg: DownstreamMsg):
        self.msg = msg
        self.acked: asyncio.Future = asyncio.get_running_loop().create_future()

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.msg)


class Output(Awaiting):
    """A port output command: acknowledged once it starts, `done` resolves once it ends"""

    def __init__(self, msg: MsgPortOutput):
        super().__init__(msg)
        self.done: asyncio.Future = asyncio.get_running_loop().create_future()
        self.running = False


def _resolve(future: asyncio.Future, result=None) -> None:
    if not future.done():  # a caller may have stopped waiting
        future.set_result(result)


def _fail(future: asyncio.Future, exc: BaseException) -> None:
    if not future.done():
        future.set_exception(exc)
        future.exception()  # nobody may be waiting any more: mark retrieved to keep asyncio quiet


class Requests:
    def __init__(self):
        self._unacked: List[Awaiting] = []  # in the order sent
        self._ports: Dict[int, Deque[Output]] = {}

    def expect_reply(self, msg: DownstreamMsg) -> Awaiting:
        item = Awaiting(msg)
        self._unacked.append(item)
        return item

    def expect_output(self, msg: MsgPortOutput) -> Output:
        item = Output(msg)
        self._unacked.append(item)
        self._ports.setdefault(msg.port, deque()).append(item)
        return item

    def forget(self, item: Awaiting) -> None:
        """Stop tracking a command its caller gave up on"""
        if item in self._unacked:
            self._unacked.remove(item)
        if isinstance(item, Output):
            queue = self._ports.get(item.msg.port)
            if queue and item in queue:
                queue.remove(item)

    def fail_all(self, exc: BaseException) -> None:
        for item in self._unacked:
            _fail(item.acked, exc)
        for queue in self._ports.values():
            for item in queue:
                _fail(item.done, exc)
        self._unacked.clear()
        self._ports.clear()

    def on_message(self, msg: UpstreamMsg) -> None:
        if isinstance(msg, MsgGenericError):
            self._on_error(msg)
        elif isinstance(msg, MsgPortOutputFeedback):
            self._on_feedback(msg)
        else:
            self._on_reply(msg)

    def _ack(self, item: Awaiting, reply: Optional[UpstreamMsg] = None) -> None:
        if item in self._unacked:
            self._unacked.remove(item)
        _resolve(item.acked, reply)

    def _on_reply(self, msg: UpstreamMsg) -> None:
        for item in self._unacked:
            if not isinstance(item, Output) and item.msg.is_reply(msg):
                log.debug("Reply to %r: %r", item.msg, msg)
                self._ack(item, msg)
                return

    def _on_error(self, msg: MsgGenericError) -> None:
        for item in self._unacked:
            if item.msg.TYPE == msg.cmd:
                log.warning("Command %r failed: %s", item.msg, msg.message())
                exc = CommandFailed(msg.message(), msg.cmd, msg.err)
                self.forget(item)
                _fail(item.acked, exc)
                if isinstance(item, Output):
                    _fail(item.done, exc)
                return
        log.warning("Error for no pending command: %s", msg.message())

    def _on_feedback(self, msg: MsgPortOutputFeedback) -> None:
        queue = self._ports.get(msg.port)
        if not queue:
            log.debug("Feedback on port 0x%x with no pending commands: %r", msg.port, msg)
            return

        running = queue[0] if queue[0].running else None
        if msg.is_discarded():
            if running:  # another command took over the port
                self._end(queue, running, CommandDiscarded("Interrupted on port 0x%x" % msg.port))
                running = None
            elif not (msg.is_in_progress() or msg.is_completed()):  # nothing took over: the new one was rejected
                rejected = queue[0]
                self._end(queue, rejected, CommandDiscarded("Port 0x%x rejected %r" % (msg.port, rejected.msg)))
                return

        if msg.is_completed() and queue:
            finished = running or queue[0]  # a command may complete without reporting progress first
            self._end(queue, finished)

        if msg.is_in_progress():
            starting = next((item for item in queue if not item.running), None)
            if starting:
                starting.running = True
                self._ack(starting)

    def _end(self, queue: Deque[Output], item: Output, exc: Optional[BaseException] = None) -> None:
        queue.remove(item)
        if exc is None:
            self._ack(item)
            _resolve(item.done)
        else:
            if item in self._unacked:
                self._unacked.remove(item)
            _fail(item.acked, exc)
            _fail(item.done, exc)
