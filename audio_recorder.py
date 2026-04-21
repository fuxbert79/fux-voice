"""Audio-Aufnahme mit Pause/Flush-Logik.

Die Besonderheit: Ein Pause-Event gibt den aktuellen Buffer frei (Callback),
danach startet ein neuer Buffer weiter. So kann der Text schon
eingefuegt werden waehrend die Aufnahme fortgesetzt wird.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

ChunkCallback = Callable[[np.ndarray, int], None]


class AudioRecorder:
    """Nimmt Audio in einem Hintergrund-Thread auf."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: Optional[int | str] = None,
        chunk_callback: Optional[ChunkCallback] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.chunk_callback = chunk_callback

        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._buffer: list[np.ndarray] = []
        self._buffer_lock = threading.Lock()

        self._is_recording = False
        self._is_paused = False
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def _stream_callback(self, indata, frames, time_info, status) -> None:
        if status:
            logger.warning("Audio-Stream-Status: %s", status)
        if not self._is_paused:
            self._audio_queue.put(indata.copy())

    def _worker(self) -> None:
        """Konsumiert Audio-Queue und haengt an Buffer an."""
        while not self._stop_event.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            with self._buffer_lock:
                self._buffer.append(chunk)

    def start(self) -> None:
        """Startet die Aufnahme."""
        if self._is_recording:
            logger.warning("Aufnahme laeuft bereits")
            return

        logger.info("Starte Aufnahme (%d Hz, %d Kanal/Kanaele)", self.sample_rate, self.channels)
        self._is_recording = True
        self._is_paused = False
        self._stop_event.clear()
        with self._buffer_lock:
            self._buffer = []

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            device=self.device,
            callback=self._stream_callback,
            dtype="float32",
        )
        self._stream.start()

        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def pause_and_flush(self) -> Optional[np.ndarray]:
        """Pausiert Aufnahme, gibt aktuellen Buffer zurueck und startet mit leerem Buffer weiter.

        Returns:
            Audio-Array oder None wenn Buffer leer war.
        """
        if not self._is_recording or self._is_paused:
            return None

        self._is_paused = True
        logger.info("Pause — flush aktueller Buffer")

        with self._buffer_lock:
            if not self._buffer:
                return None
            audio = np.concatenate(self._buffer, axis=0)
            self._buffer = []

        if self.chunk_callback:
            try:
                self.chunk_callback(audio, self.sample_rate)
            except Exception:
                logger.exception("Fehler in chunk_callback")

        return audio

    def resume(self) -> None:
        """Setzt pausierte Aufnahme fort."""
        if not self._is_recording:
            return
        self._is_paused = False
        logger.info("Aufnahme fortgesetzt")

    def stop(self, *, discard: bool = False) -> Optional[np.ndarray]:
        """Stoppt Aufnahme und gibt finalen Buffer zurueck.

        Args:
            discard: Wenn True, wird der Buffer verworfen (fuer Cancel).
        """
        if not self._is_recording:
            return None

        logger.info("Stoppe Aufnahme (discard=%s)", discard)
        self._is_recording = False
        self._is_paused = False
        self._stop_event.set()

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self._worker_thread is not None:
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None

        while not self._audio_queue.empty():
            try:
                chunk = self._audio_queue.get_nowait()
            except queue.Empty:
                break
            with self._buffer_lock:
                self._buffer.append(chunk)

        with self._buffer_lock:
            if discard or not self._buffer:
                self._buffer = []
                return None
            audio = np.concatenate(self._buffer, axis=0)
            self._buffer = []
        return audio
