# python internals
from __future__ import annotations
from typing import Callable, Optional, Generic, TypeVar
import time
# internal packages
from .buffer import Buffer
# external packages
from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal

T = TypeVar("T")
class Scheduler(QObject, Generic[T]):
    stepOccurred = pyqtSignal(int)
    def __init__(self, func: Callable[[T], None], max_fps: int, parent: Optional[QObject] = None) -> None:
        if max_fps <= 0: raise ValueError("FPS value must be greater than 0")

        super().__init__(parent)

        self.__func: Optional[Callable[[T], None]] = func
        self.__buffer: Buffer[T] = Buffer(int(0.9 * max_fps))
        self.__blocked_until: float = 0.0

        self.__iter: int = 0
        self.__dt: float = 1.0 / max_fps
        self.__last_step: float = 0.0
        self.__fps: float = 0.0

        self.__timer = QTimer(self)
        self.__timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.__timer.timeout.connect(self.step)
        self.__timer.start(0)
    def step(self) -> None:
        if self.__func is None: return

        curr_step = time.monotonic()
        if curr_step < self.__blocked_until or curr_step - self.__last_step < self.__dt: return

        value = self.__buffer.pop()
        if value is None: return

        self.__fps = 1/(curr_step - self.__last_step) if self.__last_step > 0 else 0
        self.__last_step = curr_step
        self.__func(value)

        self.__iter+= 1
        self.stepOccurred.emit(self.__iter)
    @property
    def buffer(self) -> Buffer[T]:
        return self.__buffer
    @property
    def fps(self) -> float:
        return self.__fps
    def block(self, t: Optional[float] = None) -> None:
        unblock_time = float("inf") if t is None else time.monotonic() + t
        if unblock_time > self.__blocked_until:
            self.__blocked_until = unblock_time
    def unblock(self) -> None:
        self.__blocked_until = 0.0
    def abort(self) -> None:
        self.__func = None
        self.__timer.stop()

__all__ = ['Scheduler']
