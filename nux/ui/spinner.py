# ui/spinner.py
# Universal spinner handle with FIFO queue for Nux.

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from yaspin import yaspin

if TYPE_CHECKING:
    from yaspin.core import Yaspin

@dataclass
class SpinnerState:
    text: str = ""
    style: str = "toggle10"


class SpinnerHandle:
    # Per-session spinner with a FIFO queue:
    #   - push() updates the live spinner immediately (if active) and queues
    #     the state for the next tick.
    #   - write() writes text to the top of the spinners, ensuring text not get
    #     overwritten by \r carriage returm.
    #   - tick() pops the next queued state and applies it.
    #   - start()/stop() manage the underlying yaspin instance.
    #   - push() is safe to call even when no spinner is live (the state is
    #     just queued and will be picked up on the next start/tick).

    def __init__(self) -> None:
        self._queue: list[SpinnerState] = []
        self._current = SpinnerState()
        self._instance: Yaspin | None = None

    def write(self, text: str):
        self._instance.write(text)

    def push(self, text: str, style: str | None = None) -> None:
        # Push a new spinner state and apply it immediately if live.
        state = SpinnerState(text=text, style=style or self._current.style)
        self._queue.append(state)
        self._apply(state)

    def tick(self) -> None:
        # Pop and apply the next queued state (no-op if queue is empty).
        if not self._queue:
            return
        self._current = self._queue.pop(0)
        self._apply(self._current)

    def start(self) -> None:
        # Start the live yaspin spinner (no-op if stdout is not a TTY).
        if not sys.stdout.isatty():
            return
        if self._instance is not None:
            return
        self._instance = yaspin(self._current.style, text=self._current.text)
        self._instance.__enter__()

    def stop(self) -> None:
        # Stop and tear down the live yaspin spinner.
        if self._instance is None:
            return
        self._instance.__exit__(None, None, None)
        self._instance = None

    def clear(self) -> None:
        # Clear the queue and reset to default state.
        self._queue.clear()
        self._current = SpinnerState()
        self._apply(self._current)

    def reset(self) -> None:
        # Clear queue, reset state, and restart spinner with defaults.
        self.clear()
        if self._instance is not None:
            self.stop()
            self.start()

    @property
    def current(self) -> SpinnerState:
        return self._current

    # -- internal --

    def _apply(self, state: SpinnerState) -> None:
        # Push state to the live yaspin instance (if active).
        self._current = state
        if self._instance is not None:
            self._instance.text = state.text
