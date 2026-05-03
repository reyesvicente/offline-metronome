#!/usr/bin/env python3

import sys
import time
import threading
import os

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSlider, QLineEdit
)

from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

import numpy as np
import sounddevice as sd


# ─────────────────────────────────────────────
# AUDIO ENGINE (100% STABLE - Qt backend)
# ─────────────────────────────────────────────
class AudioEngine:
    def __init__(self):
        self.sr = 44100

        # pre-generate click buffers
        self.click = self._make_click(800)
        self.accent = self._make_click(1200)

    def _make_click(self, freq):
        t = np.linspace(0, 0.03, int(self.sr * 0.03), False)
        wave = np.sin(2 * np.pi * freq * t)
        env = np.exp(-t * 80)
        audio = (wave * env * 0.3).astype(np.float32)
        stereo = np.column_stack([audio, audio])
        return stereo

    def play(self, accent=False):
        try:
            sd.play(self.accent if accent else self.click,
                    samplerate=self.sr,
                    blocking=False)
        except Exception as e:
            print("Audio error:", e)


# ─────────────────────────────────────────────
# THREAD SIGNALS
# ─────────────────────────────────────────────
class Signals(QObject):
    beat = pyqtSignal(bool)


# ─────────────────────────────────────────────
# METRONOME ENGINE (stable timing loop)
# ─────────────────────────────────────────────
class Metronome(threading.Thread):
    def __init__(self, bpm_getter, beats_getter, signals):
        super().__init__(daemon=True)
        self.bpm_getter = bpm_getter
        self.beats_getter = beats_getter
        self.signals = signals
        self.running = False

    def start_engine(self):
        self.running = True
        self.start()

    def stop_engine(self):
        self.running = False

    def run(self):
        next_tick = time.perf_counter()
        idx = 0

        while self.running:
            bpm = max(30, min(300, self.bpm_getter()))
            beats = max(1, self.beats_getter())

            now = time.perf_counter()

            if now >= next_tick:
                self.signals.beat.emit(idx == 0)
                idx = (idx + 1) % beats
                next_tick += 60.0 / bpm

                if next_tick < now:
                    next_tick = now + 60.0 / bpm
            else:
                time.sleep(0.001)


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
class MetronomeApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Metronome (Stable PyQt6)")
        self.setFixedSize(400, 460)

        self.audio = AudioEngine()
        self.signals = Signals()

        self.bpm = 120
        self.beats = 4
        self.running = False

        self.tap_times = []

        self._build_ui()

        self.signals.beat.connect(self.on_beat)

        self.engine = Metronome(
            lambda: self.bpm,
            lambda: self.beats,
            self.signals
        )

    # ─────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout()

        title = QLabel("METRONOME")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # BPM input
        self.bpm_input = QLineEdit(str(self.bpm))
        self.bpm_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bpm_input.setStyleSheet("font-size: 28px;")
        self.bpm_input.textChanged.connect(self.update_bpm)
        layout.addWidget(self.bpm_input)

        # slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(30, 300)
        self.slider.setValue(self.bpm)
        self.slider.valueChanged.connect(self.slider_changed)
        layout.addWidget(self.slider)

        # beats
        row = QHBoxLayout()
        self.beat_label = QLabel("Beats: 4")
        row.addWidget(self.beat_label)

        for n in [2, 3, 4, 6, 8]:
            btn = QPushButton(str(n))
            btn.clicked.connect(lambda _, x=n: self.set_beats(x))
            row.addWidget(btn)

        layout.addLayout(row)

        # play button
        self.play_btn = QPushButton("PLAY")
        self.play_btn.clicked.connect(self.toggle)
        self.play_btn.setStyleSheet("""
            font-size: 18px;
            padding: 10px;
            background: #2ECC71;
            color: white;
        """)
        layout.addWidget(self.play_btn)

        # tap tempo
        self.tap_btn = QPushButton("TAP TEMPO")
        self.tap_btn.clicked.connect(self.tap_tempo)
        layout.addWidget(self.tap_btn)

        self.setLayout(layout)

    # ─────────────────────────────────────────────
    # BPM LOGIC
    # ─────────────────────────────────────────────
    def update_bpm(self):
        try:
            self.bpm = int(self.bpm_input.text())
            self.slider.setValue(self.bpm)
        except ValueError:
            pass

    def slider_changed(self, v):
        self.bpm = v
        self.bpm_input.setText(str(v))

    def set_beats(self, b):
        self.beats = b
        self.beat_label.setText(f"Beats: {b}")

    # ─────────────────────────────────────────────
    # TAP TEMPO (averaged)
    # ─────────────────────────────────────────────
    def tap_tempo(self):
        now = time.time()

        self.tap_times.append(now)
        self.tap_times = self.tap_times[-4:]

        if len(self.tap_times) < 2:
            return

        intervals = [
            self.tap_times[i] - self.tap_times[i - 1]
            for i in range(1, len(self.tap_times))
        ]

        avg = sum(intervals) / len(intervals)
        bpm = int(60 / avg)

        self.bpm = max(30, min(300, bpm))

        self.slider.setValue(self.bpm)
        self.bpm_input.setText(str(self.bpm))

    # ─────────────────────────────────────────────
    # ENGINE CONTROL
    # ─────────────────────────────────────────────
    def toggle(self):
        if self.running:
            self.engine.stop_engine()
            self.play_btn.setText("PLAY")
            self.play_btn.setStyleSheet("""
                font-size: 18px;
                padding: 10px;
                background: #2ECC71;
                color: white;
            """)
        else:
            if not self.engine.is_alive():
                self.engine = Metronome(
                    lambda: self.bpm,
                    lambda: self.beats,
                    self.signals
                )
                self.engine.start_engine()

            self.play_btn.setText("STOP")
            self.play_btn.setStyleSheet("""
                font-size: 18px;
                padding: 10px;
                background: #E94560;
                color: white;
            """)

        self.running = not self.running

    # ─────────────────────────────────────────────
    # BEAT HANDLER
    # ─────────────────────────────────────────────
    def on_beat(self, accent):
        self.audio.play(accent)


# ─────────────────────────────────────────────
# RUN APP
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MetronomeApp()
    window.show()
    sys.exit(app.exec())