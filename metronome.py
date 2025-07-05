import sys
import numpy as np
import sounddevice as sd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, 
                            QHBoxLayout, QLabel, QSpinBox, QSlider, QComboBox)
from PyQt6.QtCore import QTimer, Qt

class Metronome(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Metronome")
        self.setMinimumSize(400, 300)
        
        # Audio settings
        self.sample_rate = 44100
        self.volume = 0.5
        self.beat_duration = 0.1  # seconds
        self.beat_freq = 880  # Hz
        
        # Metronome state
        self.is_playing = False
        self.tempo = 120
        self.beats_per_measure = 4
        self.current_beat = 0
        
        # Initialize UI
        self.init_ui()
        
        # Timer for metronome ticks
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        
    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Tempo control
        tempo_layout = QHBoxLayout()
        tempo_layout.addWidget(QLabel("Tempo (BPM):"))
        
        self.tempo_slider = QSlider(Qt.Orientation.Horizontal)
        self.tempo_slider.setRange(40, 208)
        self.tempo_slider.setValue(self.tempo)
        self.tempo_slider.valueChanged.connect(self.set_tempo)
        tempo_layout.addWidget(self.tempo_slider)
        
        self.tempo_spinbox = QSpinBox()
        self.tempo_spinbox.setRange(40, 208)
        self.tempo_spinbox.setValue(self.tempo)
        self.tempo_spinbox.valueChanged.connect(self.set_tempo)
        tempo_layout.addWidget(self.tempo_spinbox)
        
        layout.addLayout(tempo_layout)
        
        # Beats per measure
        measure_layout = QHBoxLayout()
        measure_layout.addWidget(QLabel("Beats per measure:"))
        
        self.measure_combo = QComboBox()
        self.measure_combo.addItems(["2", "3", "4", "6", "8"])
        self.measure_combo.setCurrentText(str(self.beats_per_measure))
        self.measure_combo.currentTextChanged.connect(self.set_beats_per_measure)
        measure_layout.addWidget(self.measure_combo)
        
        layout.addLayout(measure_layout)
        
        # Play/Stop button
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        layout.addWidget(self.play_button)
        
        # Beat indicator
        self.beat_indicator = QLabel("")
        self.beat_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beat_indicator.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.beat_indicator)
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.volume * 100))
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)
        
        layout.addLayout(volume_layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def set_tempo(self, value):
        self.tempo = value
        if self.tempo_slider.value() != value:
            self.tempo_slider.setValue(value)
        if self.tempo_spinbox.value() != value:
            self.tempo_spinbox.setValue(value)
    
    def set_beats_per_measure(self, value):
        self.beats_per_measure = int(value)
    
    def set_volume(self, value):
        self.volume = value / 100.0
    
    def toggle_play(self):
        if self.is_playing:
            self.stop_metronome()
        else:
            self.start_metronome()
    
    def start_metronome(self):
        self.is_playing = True
        self.play_button.setText("Stop")
        self.current_beat = 0
        self.tick()  # Start immediately
        interval = int((60.0 / self.tempo) * 1000)  # Convert BPM to milliseconds
        self.timer.start(interval)
    
    def stop_metronome(self):
        self.is_playing = False
        self.play_button.setText("Play")
        self.timer.stop()
        self.beat_indicator.setText("")
    
    def tick(self):
        # Play sound
        self.play_click()
        
        # Update beat indicator
        self.current_beat = (self.current_beat % self.beats_per_measure) + 1
        self.beat_indicator.setText(str(self.current_beat))
    
    def play_click(self):
        # Generate a beep sound
        t = np.linspace(0, self.beat_duration, int(self.sample_rate * self.beat_duration), False)
        # Different sound for first beat
        if self.current_beat == 1:
            freq = self.beat_freq * 1.5  # Higher pitch for first beat
        else:
            freq = self.beat_freq
        
        # Generate tone
        tone = np.sin(2 * np.pi * freq * t) * self.volume
        
        # Apply envelope for click sound
        envelope = np.ones_like(t)
        attack = int(0.01 * len(t))
        decay = int(0.1 * len(t))
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack:decay] = np.linspace(1, 0.2, decay - attack)
        envelope[decay:] = np.linspace(0.2, 0, len(t) - decay)
        
        tone = tone * envelope
        
        # Play the sound
        sd.play(tone, self.sample_rate, blocking=False)

def main():
    app = QApplication(sys.argv)
    metronome = Metronome()
    metronome.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
