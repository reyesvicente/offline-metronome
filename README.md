# Cross-Platform Metronome

A simple, offline metronome application that works on Windows, macOS, and Linux (Debian/Ubuntu).

## Features
- Adjustable tempo (40-250 BPM)
- Configurable beats per measure (2, 3, 4, 6, or 8)
- Visual beat indicator
- Adjustable volume
- Different sounds for downbeat and other beats

## Requirements
- Python 3.7 or higher
- pip (Python package manager)

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

### Linux/macOS
```bash
python3 metronome.py
```

### Windows
```bash
python metronome.py
```

## Usage
1. Adjust the tempo using the slider or the spinbox
2. Select the number of beats per measure
3. Click the "Play" button to start the metronome
4. Click "Stop" to stop the metronome
5. Adjust the volume using the volume slider

## Building Executables (Optional)

To create standalone executables for easier distribution:

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Build the executable:
```bash
# On Windows
pyinstaller --onefile --windowed metronome.py

# On macOS/Linux
pyinstaller --onefile metronome.py
```

The executable will be in the `dist` directory.

## License
This project is open source and available under the MIT License.
