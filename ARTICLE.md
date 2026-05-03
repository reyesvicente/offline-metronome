# Building a Metronome Desktop App for Ubuntu with Python

A metronome is one of the most fundamental tools a musician can have. This article walks through building a fully functional, self-contained metronome desktop application for Ubuntu using Python — no audio files, no external GUI frameworks, no Electron overhead. Just `tkinter`, `numpy`, and `sounddevice`.

---

## Features at a Glance

- BPM range: 30 – 300
- Real-time BPM control via slider, ±1/±5 step buttons, and direct text entry
- Tap Tempo (button or `T` key)
- Time signatures: 2, 3, 4, 6, 8 beats per bar
- Animated beat indicator dots (red downbeat, teal subdivisions)
- Italian tempo labels (Grave → Prestissimo) that update live
- Keyboard shortcuts: `Space` to play/stop, `T` to tap
- Ubuntu application menu integration via a `.desktop` file

---

## Project Structure

```
TempoApp/
├── env/               # Python virtualenv
├── metronome.py       # Entire application (~375 lines)
├── requirements.txt   # sounddevice, numpy
└── install.sh         # Installs deps + registers desktop launcher
```

The entire app lives in one file. There are no Django models, no REST endpoints, no React components — just a focused desktop tool.

---

## Installation

```bash
# Clone or enter the project folder
cd ~/Code/TempoApp

# Activate the virtualenv and install dependencies
source env/bin/activate
pip install -r requirements.txt

# Run
python metronome.py
```

To register it in the Ubuntu application menu, run `install.sh` once:

```bash
bash install.sh
```

This writes a `.desktop` file to `~/.local/share/applications/` pointing at the virtualenv Python and the script, so GNOME can launch it like any installed app.

---

## Architecture: Three Layers

The app is split into three clearly separated concerns:

```
AudioEngine        — synthesises and plays click sounds
MetronomeEngine    — owns the timing loop on a background thread
MetronomeApp       — tkinter UI, wires the other two together
```

Each layer knows nothing about the one above it. `AudioEngine` has no concept of BPM. `MetronomeEngine` has no concept of widgets. `MetronomeApp` simply connects them.

---

## Layer 1: Audio — `AudioEngine`

```python
class AudioEngine:
    SR = 44100

    def __init__(self):
        if not AUDIO_OK:
            return
        self._accent = self._click(freq=1200, dur=0.055, vol=1.0)
        self._normal = self._click(freq=800,  dur=0.045, vol=0.72)
```

The two click sounds — one accented (downbeat) and one normal — are synthesised once at startup and cached as NumPy arrays. Playing a cached array is nearly instant and avoids any per-beat allocation.

### Synthesising a click from scratch

```python
def _click(self, freq, dur, vol):
    t = np.linspace(0, dur, int(self.SR * dur), False)
    wave = np.sin(2 * np.pi * freq * t)
    env  = np.exp(-t * 45)
    mono = (wave * env * vol).astype(np.float32)
    return np.column_stack([mono, mono])   # stereo
```

This is digital synthesis in five lines:

1. **`t`** — a time axis from `0` to `dur` seconds, sampled at 44 100 Hz.
2. **`wave`** — a pure sine wave at `freq` Hz. The formula `sin(2πft)` is the standard discrete sine.
3. **`env`** — an exponential decay envelope. `exp(-t * 45)` starts at 1.0 and falls to near zero in ~55 ms. The decay rate `45` was tuned by ear — higher values give a shorter, sharper click.
4. **`mono`** — the wave multiplied by the envelope and the volume scalar, cast to `float32` which `sounddevice` expects.
5. The array is stacked into two identical columns to produce stereo output.

The accent uses 1200 Hz (bright, cutting), the normal click uses 800 Hz (softer, lower). Together they give audible hierarchy without needing separate sample files.

### Playing

```python
def play(self, accent: bool):
    if not AUDIO_OK:
        return
    try:
        sd.play(self._accent if accent else self._normal, self.SR)
    except Exception:
        pass
```

`sd.play()` is non-blocking — it hands the buffer to PortAudio and returns immediately, so it never stalls the timing loop.

The graceful import at the top of the file means the app runs in visual-only mode even without `sounddevice` installed:

```python
try:
    import numpy as np
    import sounddevice as sd
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False
```

---

## Layer 2: Timing — `MetronomeEngine`

Accurate timing is the hardest part of a metronome. `time.sleep(60/bpm)` drifts badly over time because it sleeps for *at least* the requested duration and accumulates error each beat. The engine instead uses an **absolute deadline loop**.

```python
def _loop(self):
    next_t = time.perf_counter()
    while self.running:
        now = time.perf_counter()
        if now >= next_t:
            idx = self._beat_idx
            self.audio.play(accent=(idx == 0))
            self.on_beat(idx)
            self._beat_idx = (idx + 1) % self.beats
            next_t += 60.0 / self.bpm        # advance deadline by one beat
            if next_t < now:                  # fell behind — re-anchor
                next_t = now + 60.0 / self.bpm
        else:
            time.sleep(min((next_t - now) * 0.85, 0.002))
```

Key points:

- **`time.perf_counter()`** is the highest-resolution clock available in Python (nanosecond precision on Linux). It never drifts like wall-clock time.
- **`next_t += 60.0 / bpm`** advances the absolute deadline by exactly one beat interval. Errors do not accumulate — each beat is measured from the previous beat's scheduled time, not the actual time.
- **The `if next_t < now` guard** handles the edge case where the system was suspended or the thread starved. Rather than firing a burst of catch-up beats, it simply re-anchors to now.
- **The `else` branch** avoids busy-waiting by sleeping `85%` of the remaining time. Waking slightly early means we never overshoot the deadline. The `0.002` cap ensures the thread checks at least every 2 ms.

The loop runs on a **daemon thread**:

```python
self._thread = threading.Thread(target=self._loop, daemon=True)
self._thread.start()
```

`daemon=True` means the thread is killed automatically when the main window closes, so there is no explicit teardown needed.

BPM changes take effect immediately because `self.bpm` is read inside the loop on every beat — no restart required.

---

## Layer 3: UI — `MetronomeApp` and `RoundedButton`

### The `RoundedButton`

tkinter's built-in `Button` widget cannot have rounded corners. `RoundedButton` solves this by subclassing `tk.Canvas` and drawing a polygon with `smooth=True`:

```python
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
```

Each pair in `pts` is a vertex of the bounding rectangle, inset by `r` at every corner. With `smooth=True` tkinter draws Bezier curves through the points, producing the rounded effect.

The press/release feedback uses `stipple`:

```python
def _press(self, _e):
    self.itemconfig(self._rect, stipple="gray50")   # dims the fill to 50% opacity

def _release(self, _e):
    self.itemconfig(self._rect, stipple="")
    self._command()
```

`stipple="gray50"` is a built-in tkinter bitmap that masks every other pixel, giving a visual darkening effect without touching the colour value.

### Thread-safe UI updates

The timing loop runs on a background thread, but tkinter is **not thread-safe** — you cannot call widget methods from any thread other than the main one. The bridge is `root.after(0, ...)`:

```python
def _on_beat(self, idx):
    self.root.after(0, self._flash, idx)   # schedule on main thread
```

`root.after(0, fn, *args)` posts a callback to tkinter's event queue with zero delay. It executes on the main thread the next time the event loop runs — safely, with no locking required.

### Beat dots

The dot indicators are rebuilt from scratch whenever the time signature changes:

```python
def _set_beats(self, n, init=False):
    for w in self._dot_frame.winfo_children():
        w.destroy()
    self._beat_dots.clear()
    for _ in range(n):
        c = tk.Canvas(self._dot_frame, width=30, height=30, ...)
        c.pack(side="left", padx=6)
        oval = c.create_oval(3, 3, 27, 27, fill=C["dot_off"], outline="")
        self._beat_dots.append((c, oval))
```

Each dot is a `tk.Canvas` containing a single oval item. Storing the `(canvas, oval_id)` pair lets `_flash` call `canvas.itemconfig(oval_id, fill=color)` in O(1) without a widget lookup.

The flash itself uses a delayed reset:

```python
def _flash(self, idx):
    for i, (c, oval) in enumerate(self._beat_dots):
        if i == idx:
            color = C["beat1"] if idx == 0 else C["beatN"]
            c.itemconfig(oval, fill=color)
            self.root.after(110, lambda cv=c, ov=oval: cv.itemconfig(ov, fill=C["dot_off"]))
```

`root.after(110, ...)` schedules the colour reset 110 ms later — long enough to be visible at 300 BPM (200 ms per beat) but short enough that two rapid beats never merge visually. The `cv=c, ov=oval` default-argument capture is the standard Python closure-in-loop idiom to capture the current iteration's values rather than the final ones.

### Tap Tempo

```python
def _tap(self):
    now = time.time()
    self._tap_times = [t for t in self._tap_times if now - t < 3.0]
    self._tap_times.append(now)
    if len(self._tap_times) >= 2:
        intervals = [self._tap_times[i+1] - self._tap_times[i]
                     for i in range(len(self._tap_times) - 1)]
        avg = sum(intervals) / len(intervals)
        self._apply_bpm(round(60.0 / avg))
```

The list is filtered to only keep taps within the last 3 seconds before each new tap is added. This means tapping resets naturally after a pause — you don't need to explicitly "clear" the tap buffer. The BPM is the average over all recent intervals, smoothing out any uneven taps.

### Tempo labels

```python
def tempo_name(bpm: int) -> str:
    for limit, name in [
        (40,  "Grave"),
        (60,  "Largo"),
        ...
        (200, "Presto"),
    ]:
        if bpm < limit:
            return name
    return "Prestissimo"
```

A simple linear scan through Italian tempo markings. The table is ordered ascending, so the first match wins. This is called inside `_apply_bpm`, which is the single point all BPM changes flow through — slider, entry field, ±buttons, and tap tempo all call `_apply_bpm`, keeping the label always in sync.

---

## The `.desktop` File

Ubuntu's application launcher reads `.desktop` files from `~/.local/share/applications/`. The install script writes:

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Metronome
Exec=/home/highcenburg/Code/TempoApp/env/bin/python /home/highcenburg/Code/TempoApp/metronome.py
Icon=multimedia-volume-control
Terminal=false
Categories=AudioVideo;Music;Utility;
Keywords=metronome;bpm;tempo;beat;music;
```

`Exec` points directly to the virtualenv Python so the app always runs with its own isolated dependencies, regardless of what is installed system-wide. `Icon=multimedia-volume-control` reuses an icon already present in most Ubuntu themes.

---

## Design Decisions

| Decision | Reason |
|---|---|
| Synthesise clicks with NumPy | No audio files to bundle or ship; works on any machine |
| Absolute deadline timing loop | Cumulative drift from `time.sleep` would make the metronome unusable within a minute |
| Daemon thread | Clean shutdown with zero teardown code |
| `root.after(0, ...)` bridge | Only safe way to touch tkinter widgets from a background thread |
| Single `_apply_bpm` function | All inputs converge here so tempo label, slider, and entry are always consistent |
| `RoundedButton` as `Canvas` | tkinter's `Button` has no border-radius; Canvas polygons with `smooth=True` are the idiomatic workaround |

---

## Running

```bash
# With virtualenv active
source env/bin/activate
python metronome.py

# Without activating
env/bin/python metronome.py
```

Keyboard shortcuts:

| Key | Action |
|---|---|
| `Space` | Play / Stop |
| `T` | Tap Tempo |
| `Enter` | Commit typed BPM |

---

## Conclusion

The app clocks in at 375 lines across one file. The three-layer separation — audio synthesis, timing, and UI — keeps each piece independently testable and easy to reason about. The hardest part, accurate timing, is solved by the absolute-deadline loop pattern: advance `next_t` by a fixed interval on each beat and never let errors accumulate.
