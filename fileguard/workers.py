"""
Worker Thread Management for FileGuard.
Provides non-blocking background workers with thread-safe queue dispatching to Tkinter.
"""
import queue
import threading
from typing import Callable, Any, Optional


class WorkerTask(threading.Thread):
    def __init__(
        self,
        target: Callable[..., Any],
        args: tuple = (),
        kwargs: dict = None,
        callback_queue: Optional[queue.Queue] = None,
        task_id: str = "generic_task"
    ):
        super().__init__(daemon=True)
        self.target = target
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.callback_queue = callback_queue
        self.task_id = task_id
        self._cancelled = False
        self.result = None
        self.error = None

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self):
        try:
            self.result = self.target(*self.args, **self.kwargs)
            if self.callback_queue:
                self.callback_queue.put({
                    "task_id": self.task_id,
                    "status": "completed",
                    "result": self.result,
                    "error": None
                })
        except Exception as e:
            self.error = e
            if self.callback_queue:
                self.callback_queue.put({
                    "task_id": self.task_id,
                    "status": "failed",
                    "result": None,
                    "error": e
                })


def run_in_background(
    target: Callable[..., Any],
    args: tuple = (),
    kwargs: dict = None,
    callback_queue: Optional[queue.Queue] = None,
    task_id: str = "task"
) -> WorkerTask:
    """Helper to instantiate and immediately start a background worker task."""
    task = WorkerTask(target, args, kwargs, callback_queue, task_id)
    task.start()
    return task
