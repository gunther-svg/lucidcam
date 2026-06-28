"""
BaseProvider — abstract interface for LucidCam video processing backends.

All backends (Decart API, HuggingFace Space, local model, etc.) should
implement this interface so app.py can swap them without changes.
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class BaseProvider(ABC):
    """
    Abstract base class for a LucidCam video processing backend.

    Lifecycle:
        provider = MyProvider(...)
        await provider.start()          # establish connection / load model
        ...
        provider.push_frame(frame_rgb)  # called every camera frame (~24fps)
        frame = provider.get_output_frame()  # called every output tick (~24fps)
        ...
        await provider.stop()           # cleanup
    """

    @property
    @abstractmethod
    def status(self) -> str:
        """
        Current provider status string.
        One of: "disconnected", "connecting", "warming_up", "live", "error"
        """
        ...

    @abstractmethod
    async def start(self) -> None:
        """
        Initialise the provider: connect to API, poll health, load model, etc.
        Should update self.status to "live" when ready.
        May raise RuntimeError on unrecoverable errors.
        """
        ...

    @abstractmethod
    def push_frame(self, frame_rgb: np.ndarray) -> None:
        """
        Push a new raw camera frame into the provider's input buffer.
        Called at camera FPS (typically 24fps). Must be non-blocking.

        Args:
            frame_rgb: HxWx3 uint8 numpy array in RGB colour order.
        """
        ...

    @abstractmethod
    def get_output_frame(self) -> Optional[np.ndarray]:
        """
        Get the next processed frame for display / virtual camera output.
        Called at output FPS (typically 24fps). Must be non-blocking.

        Returns:
            HxWx3 uint8 numpy array in RGB colour order, or None if no
            processed frame is available yet (repeat last frame or show spinner).
        """
        ...

    def set_prompt(self, prompt: str) -> None:
        """
        Update the text prompt used for processing.
        Default implementation is a no-op; override in subclasses.
        """

    @abstractmethod
    async def stop(self) -> None:
        """
        Gracefully shut down the provider: cancel tasks, close connections.
        """
        ...
