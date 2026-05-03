# TempoApp (Offline Metronome)

A professional-grade, lightweight, and stable offline metronome application built with Python and PyQt6. Designed for musicians who need a reliable timing tool without the bloat of web-based alternatives.

![Metronome Preview](https://via.placeholder.com/400x460.png?text=TempoApp+Interface)

## Key Features

- **Stable Timing Engine**: High-precision threading model to ensure consistent beats even under CPU load.
- **Wide Tempo Range**: Adjustable from **30 to 300 BPM** via slider or direct input.
- **Tap Tempo**: Intuitive tempo detection by tapping—perfect for finding the BPM of a song on the fly.
- **Beat Subdivisions**: Quick presets for common time signatures (2, 3, 4, 6, 8 beats per measure).
- **Accented Downbeats**: Clear audio distinction for the first beat of every measure.
- **Offline First**: Zero dependencies on internet connectivity once installed.
- **Linux Integration**: Includes an installation script that creates a native desktop entry.

## Requirements

- **Python 3.10+**
- **System Audio Drivers** (ALSA/PulseAudio/PipeWire for Linux, CoreAudio for macOS, WASAPI for Windows)

## Installation

### Linux (Recommended)
The included installation script automates the environment setup and adds the app to your application menu:

```bash
chmod +x install.sh
./install.sh
```

### Manual Installation (All Platforms)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/reyesvicente/offline-metronome.git
   cd offline-metronome
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the app**:
   ```bash
   python metronome.py
   ```
2. **Set Tempo**: Use the horizontal slider for coarse adjustment or type the exact BPM in the input field.
3. **Select Beats**: Click one of the preset buttons (2, 3, 4, 6, 8) to set the measure length.
4. **Tap Tempo**: Tap the "TAP TEMPO" button repeatedly at the desired rhythm to calculate the BPM.
5. **Play/Stop**: Use the primary green/red button to control the engine.

## Technical Details

- **Backend**: Python 3
- **GUI Framework**: PyQt6
- **Audio Engine**: `sounddevice` + `numpy` (Sine wave generation with exponential decay)
- **Concurrency**: Dedicated `threading.Thread` for the timing loop using `time.perf_counter()` for sub-millisecond precision.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Created by Vicente G. Reyes*