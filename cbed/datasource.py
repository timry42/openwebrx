import math
import random
import struct
import threading
import time


class RandomWaterfallSource:
    def __init__(self, fft_size=1024, rows_per_second=12):
        self.fft_size = fft_size
        self.rows_per_second = rows_per_second
        self._subscribers = set()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._sequence = 0
        self._random = random.Random()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def subscribe(self, callback):
        with self._lock:
            self._subscribers.add(callback)

    def unsubscribe(self, callback):
        with self._lock:
            self._subscribers.discard(callback)

    def start(self, rows_per_second=None):
        if rows_per_second is not None:
            self.rows_per_second = max(1, min(30, int(rows_per_second)))
        if self.running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="random-waterfall-source", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._thread = None

    def make_frame(self):
        phase = self._sequence / 18.0
        peak_positions = (
            int(self.fft_size * (0.22 + 0.04 * math.sin(phase))),
            int(self.fft_size * (0.53 + 0.08 * math.sin(phase * 0.43))),
            int(self.fft_size * (0.78 + 0.02 * math.cos(phase * 0.71))),
        )
        values = []
        for index in range(self.fft_size):
            level = -103.0 + self._random.gauss(0, 3.2)
            for peak_index, position in enumerate(peak_positions):
                width = 3 + peak_index * 2
                distance = (index - position) / width
                level += (48 - peak_index * 7) * math.exp(-0.5 * distance * distance)
            values.append(level)

        self._sequence += 1
        return b"\x01" + struct.pack("<{}f".format(self.fft_size), *values)

    def _run(self):
        next_row = time.monotonic()
        while not self._stop_event.is_set():
            frame = self.make_frame()
            with self._lock:
                subscribers = tuple(self._subscribers)
            for callback in subscribers:
                try:
                    callback(frame)
                except (ConnectionError, OSError):
                    self.unsubscribe(callback)

            next_row += 1.0 / self.rows_per_second
            self._stop_event.wait(max(0, next_row - time.monotonic()))


class RandomCompassSource:
    def __init__(self, updates_per_second=4):
        self.updates_per_second = updates_per_second
        self._subscribers = set()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._heading = random.uniform(0, 360)
        self._random = random.Random()

    def subscribe(self, callback):
        with self._lock:
            self._subscribers.add(callback)
        if not self.running:
            self.start()

    def unsubscribe(self, callback):
        with self._lock:
            self._subscribers.discard(callback)

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="random-compass-source", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._thread = None

    def make_message(self):
        self._heading = (self._heading + self._random.uniform(-12, 12)) % 360
        return {"type": "compass", "value": {"heading": round(self._heading, 1) % 360}}

    def _run(self):
        while not self._stop_event.is_set():
            message = self.make_message()
            with self._lock:
                subscribers = tuple(self._subscribers)
            for callback in subscribers:
                try:
                    callback(message)
                except (ConnectionError, OSError):
                    self.unsubscribe(callback)
            self._stop_event.wait(1.0 / self.updates_per_second)
