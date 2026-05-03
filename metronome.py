#!/usr/bin/env python3
"""
Metronome Desktop App for Ubuntu
Requires: pip install sounddevice numpy
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import sys

try:
    import numpy as np
    import sounddevice as sd
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False
    print("Warning: sounddevice/numpy not installed. Audio disabled.", file=sys.stderr)
    print("Run: pip install sounddevice numpy", file=sys.stderr)

# ── Palette ──────────────────────────────────────────────────────────────────
C = {
    "bg":          "#1A1A2E",
    "surface":     "#16213E",
    "card":        "#0F3460",
    "accent":      "#E94560",
    "accent2":     "#533483",
    "beat1":       "#E94560",   # accent (downbeat)
    "beatN":       "#0F8B8D",   # teal (other beats)
    "dot_off":     "#2A2A4A",
    "text":        "#EAEAEA",
    "muted":       "#7A7A9D",
    "green":       "#2ECC71",
}

SANS = "Helvetica"

# ── Tempo names ───────────────────────────────────────────────────────────────
def tempo_name(bpm: int) -> str:
    for limit, name in [
        (40,  "Grave"),
        (60,  "Largo"),
        (66,  "Larghetto"),
        (76,  "Adagio"),
        (108, "Andante"),
        (120, "Moderato"),
        (156, "Allegro"),
        (176, "Vivace"),
        (200, "Presto"),
    ]:
        if bpm < limit:
            return name
    return "Prestissimo"


# ── Audio ─────────────────────────────────────────────────────────────────────
class AudioEngine:
    SR = 44100

    def __init__(self):
        if not AUDIO_OK:
            return
        self._accent = self._click(freq=1200, dur=0.055, vol=1.0)
        self._normal = self._click(freq=800,  dur=0.045, vol=0.72)

    def _click(self, freq, dur, vol):
        t = np.linspace(0, dur, int(self.SR * dur), False)
        wave = np.sin(2 * np.pi * freq * t)
        env  = np.exp(-t * 45)
        mono = (wave * env * vol).astype(np.float32)
        return np.column_stack([mono, mono])   # stereo

    def play(self, accent: bool):
        if not AUDIO_OK:
            return
        try:
            sd.play(self._accent if accent else self._normal, self.SR)
        except Exception:
            pass


# ── Timing engine ─────────────────────────────────────────────────────────────
class MetronomeEngine:
    MIN_BPM = 30
    MAX_BPM = 300

    def __init__(self, audio: AudioEngine, on_beat):
        self.audio     = audio
        self.on_beat   = on_beat   # callback(beat_index: int)
        self.bpm       = 120
        self.beats     = 4
        self.running   = False
        self._beat_idx = 0
        self._thread   = None

    def start(self):
        if self.running:
            return
        self.running   = True
        self._beat_idx = 0
        self._thread   = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        next_t = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            if now >= next_t:
                idx = self._beat_idx
                self.audio.play(accent=(idx == 0))
                self.on_beat(idx)
                self._beat_idx = (idx + 1) % self.beats
                next_t += 60.0 / self.bpm
                if next_t < now:        # fell behind – re-anchor
                    next_t = now + 60.0 / self.bpm
            else:
                time.sleep(min((next_t - now) * 0.85, 0.002))


# ── UI ────────────────────────────────────────────────────────────────────────
class RoundedButton(tk.Canvas):
    """Flat rounded-rectangle button."""

    def __init__(self, parent, text, command, width=160, height=46,
                 bg=C["accent"], fg=C["text"], font_size=13, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=parent["bg"], highlightthickness=0, **kw)
        self._text    = text
        self._command = command
        self._bg      = bg
        self._fg      = fg
        self._fs      = font_size
        self._draw()
        self.bind("<ButtonPress-1>",   self._press)
        self.bind("<ButtonRelease-1>", self._release)

    def _draw(self):
        self.delete("all")
        r, w, h = 10, int(self["width"]), int(self["height"])
        self._rect = self._rounded_rect(4, 4, w - 4, h - 4, r, self._bg)
        self._label = self.create_text(
            w // 2, h // 2, text=self._text, fill=self._fg,
            font=(SANS, self._fs, "bold"),
        )

    def _rounded_rect(self, x1, y1, x2, y2, r, fill):
        pts = [
            x1+r, y1,  x2-r, y1,
            x2,   y1,  x2,   y1+r,
            x2,   y2-r, x2,  y2,
            x2-r, y2,  x1+r, y2,
            x1,   y2,  x1,   y2-r,
            x1,   y1+r, x1,  y1,
        ]
        return self.create_polygon(pts, fill=fill, smooth=True, outline="")

    def configure_text(self, text):
        self._text = text
        self.itemconfig(self._label, text=text)

    def configure_bg(self, bg):
        self._bg = bg
        self.itemconfig(self._rect, fill=bg)

    def _press(self, _e):
        self.itemconfig(self._rect, stipple="gray50")

    def _release(self, _e):
        self.itemconfig(self._rect, stipple="")
        self._command()


class MetronomeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Metronome")
        self.root.configure(bg=C["bg"])
        self.root.resizable(False, False)

        # Center on screen
        W, H = 420, 600
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{(sx-W)//2}+{(sy-H)//2}")

        self.audio      = AudioEngine()
        self.engine     = MetronomeEngine(self.audio, self._on_beat)
        self._playing   = False
        self._tap_times: list[float] = []
        self._beat_dots: list[tuple[tk.Canvas, int]] = []

        self._build()

        self.root.bind("<space>",  lambda _: self._toggle())
        self.root.bind("<t>",      lambda _: self._tap())
        self.root.bind("<T>",      lambda _: self._tap())
        self.root.bind("<Return>", lambda _: self._commit_bpm())

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        root = self.root

        # ── Header ──
        tk.Label(root, text="METRONOME", font=(SANS, 17, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(22, 0))

        # ── BPM card ──
        card = tk.Frame(root, bg=C["surface"], bd=0)
        card.pack(padx=36, pady=16, fill="x")

        tk.Label(card, text="BPM", font=(SANS, 10),
                 bg=C["surface"], fg=C["muted"]).pack(pady=(16, 0))

        self._bpm_var = tk.StringVar(value="120")
        self._bpm_entry = tk.Entry(
            card, textvariable=self._bpm_var,
            font=(SANS, 56, "bold"), width=4, justify="center",
            bg=C["surface"], fg=C["text"], insertbackground=C["text"],
            relief="flat", bd=0,
        )
        self._bpm_entry.pack()
        self._bpm_entry.bind("<Return>",   lambda _: self._commit_bpm())
        self._bpm_entry.bind("<FocusOut>", lambda _: self._commit_bpm())

        self._tempo_lbl = tk.Label(card, text="Allegro",
                                   font=(SANS, 11, "italic"),
                                   bg=C["surface"], fg=C["accent"])
        self._tempo_lbl.pack(pady=(0, 16))

        # ── Slider ──
        self._slider = tk.Scale(
            root, from_=MetronomeEngine.MIN_BPM, to=MetronomeEngine.MAX_BPM,
            orient="horizontal", showvalue=False, length=348,
            command=self._slider_moved,
            bg=C["bg"], fg=C["text"], troughcolor=C["surface"],
            activebackground=C["accent"], highlightthickness=0, bd=0,
            sliderlength=18,
        )
        self._slider.set(120)
        self._slider.pack(pady=(0, 8))

        # ── ± buttons ──
        adj = tk.Frame(root, bg=C["bg"])
        adj.pack()
        for label, delta in [("−5", -5), ("−1", -1), ("+1", 1), ("+5", 5)]:
            tk.Button(
                adj, text=label, width=4,
                command=lambda d=delta: self._adjust(d),
                bg=C["surface"], fg=C["text"], font=(SANS, 11),
                relief="flat", bd=0, pady=5, cursor="hand2",
                activebackground=C["card"], activeforeground=C["text"],
            ).pack(side="left", padx=5)

        # ── Beat dots ──
        self._dot_frame = tk.Frame(root, bg=C["bg"])
        self._dot_frame.pack(pady=20)
        self._set_beats(4, init=True)

        # ── Time-signature radio ──
        sig = tk.Frame(root, bg=C["bg"])
        sig.pack()
        tk.Label(sig, text="Beats per bar:", font=(SANS, 10),
                 bg=C["bg"], fg=C["muted"]).pack(side="left", padx=(0, 8))
        self._beats_var = tk.IntVar(value=4)
        for n in [2, 3, 4, 6, 8]:
            tk.Radiobutton(
                sig, text=str(n), variable=self._beats_var, value=n,
                command=lambda v=n: self._set_beats(v),
                bg=C["bg"], fg=C["text"], selectcolor=C["accent"],
                activebackground=C["bg"], activeforeground=C["text"],
                font=(SANS, 11), cursor="hand2",
            ).pack(side="left", padx=4)

        # ── Play/Stop ──
        self._play_btn = RoundedButton(
            root, text="▶   PLAY", command=self._toggle,
            width=200, height=52, bg=C["green"], font_size=15,
        )
        self._play_btn.pack(pady=18)

        # ── Tap Tempo ──
        RoundedButton(
            root, text="TAP TEMPO  ( T )", command=self._tap,
            width=200, height=44, bg=C["card"], font_size=12,
        ).pack()

        if not AUDIO_OK:
            tk.Label(root, text="⚠ Audio unavailable — pip install sounddevice numpy",
                     font=(SANS, 9), bg=C["bg"], fg="#E8A838").pack(pady=8)

    # ── Beat indicator dots ───────────────────────────────────────────────────

    def _set_beats(self, n, init=False):
        if not init:
            self.engine.beats = n
        for w in self._dot_frame.winfo_children():
            w.destroy()
        self._beat_dots.clear()
        for _ in range(n):
            c = tk.Canvas(self._dot_frame, width=30, height=30,
                          bg=C["bg"], highlightthickness=0)
            c.pack(side="left", padx=6)
            oval = c.create_oval(3, 3, 27, 27, fill=C["dot_off"], outline="")
            self._beat_dots.append((c, oval))

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_beat(self, idx):
        self.root.after(0, self._flash, idx)

    def _flash(self, idx):
        for i, (c, oval) in enumerate(self._beat_dots):
            if i == idx:
                color = C["beat1"] if idx == 0 else C["beatN"]
                c.itemconfig(oval, fill=color)
                self.root.after(110, lambda cv=c, ov=oval: cv.itemconfig(ov, fill=C["dot_off"]))

    def _toggle(self):
        if self._playing:
            self.engine.stop()
            self._playing = False
            self._play_btn.configure_text("▶   PLAY")
            self._play_btn.configure_bg(C["green"])
            for c, oval in self._beat_dots:
                c.itemconfig(oval, fill=C["dot_off"])
        else:
            self.engine.start()
            self._playing = True
            self._play_btn.configure_text("⏹   STOP")
            self._play_btn.configure_bg(C["accent"])

    def _slider_moved(self, val):
        self._apply_bpm(int(float(val)))

    def _commit_bpm(self):
        try:
            bpm = int(self._bpm_var.get())
        except ValueError:
            bpm = self.engine.bpm
        self._apply_bpm(bpm)

    def _adjust(self, delta):
        self._apply_bpm(self.engine.bpm + delta)

    def _apply_bpm(self, bpm):
        bpm = max(MetronomeEngine.MIN_BPM, min(MetronomeEngine.MAX_BPM, bpm))
        self.engine.bpm = bpm
        self._bpm_var.set(str(bpm))
        self._slider.set(bpm)
        self._tempo_lbl.config(text=tempo_name(bpm))

    def _tap(self):
        now = time.time()
        self._tap_times = [t for t in self._tap_times if now - t < 3.0]
        self._tap_times.append(now)
        if len(self._tap_times) >= 2:
            intervals = [self._tap_times[i+1] - self._tap_times[i]
                         for i in range(len(self._tap_times) - 1)]
            avg = sum(intervals) / len(intervals)
            self._apply_bpm(round(60.0 / avg))

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MetronomeApp().run()
