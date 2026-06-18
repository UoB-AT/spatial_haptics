from .config import SpeakerConfig
from .audio_engine import MultiSpeakerAudioEngine
import numpy as np


class MultiSpeakerSpatialiser:
    def __init__(self, config_file=None, device_id=None):
        self.speaker_config = SpeakerConfig()

        if config_file:
            self.load_config(config_file)

        # Create audio engine with device preference
        self.audio_engine = MultiSpeakerAudioEngine(self.speaker_config, device_id=device_id)

        # Update global parameters for compatibility
        global sample_rate, tone_duration, itd_exaggeration, ild_exponent
        sample_rate = self.audio_engine.sample_rate
        tone_duration = self.audio_engine.tone_duration
        itd_exaggeration = self.audio_engine.spat_engine.itd_exaggeration
        ild_exponent = self.audio_engine.spat_engine.ild_exponent


    def load_config(self, config_file):
        """Load configuration from file."""
        success = self.speaker_config.load_from_file(config_file)
        if success:
            device_id = getattr(self.audio_engine, 'device_id', None) if hasattr(self, 'audio_engine') else None

            if hasattr(self, 'audio_engine') and self.audio_engine:
                self.audio_engine.stop_stream()

            self.audio_engine = MultiSpeakerAudioEngine(self.speaker_config, device_id=device_id)
        return success

    def save_config(self, config_file):
        """Save current configuration to file."""
        return self.speaker_config.save_to_file(config_file)

    def set_parameters(self, **kwargs):
        """Set audio and spatialization parameters."""
        self.audio_engine.set_parameters(**kwargs)

        # Update global parameters for compatibility
        global tone_duration, itd_exaggeration, ild_exponent
        if 'tone_duration' in kwargs:
            tone_duration = kwargs['tone_duration']
        if 'itd_exaggeration' in kwargs:
            itd_exaggeration = kwargs['itd_exaggeration']
        if 'ild_exponent' in kwargs:
            ild_exponent = kwargs['ild_exponent']

    def play_sound(self, x, y, freq=440, amp=0.5):
        """Play a sound at position (x, y)."""
        source_pos = np.array([x, y])
        self.audio_engine.play_tone(source_pos, freq, amp)

    def start(self):
        """Start the audio system."""
        self.audio_engine.start_stream()

    def stop(self):
        """Stop the audio system."""
        self.audio_engine.stop_stream()

    def print_info(self):
        """Print detailed configuration information."""
        self.speaker_config.print_info()
        print(f"\nChannel Map (for debugging):")
        channel_map = self.speaker_config.get_channel_map()
        for ch in sorted(channel_map.keys()):
            info = channel_map[ch]
            print(f"  Channel {ch}: {info['id']} at ({info['pos'][0] * 1000:.1f}, {info['pos'][1] * 1000:.1f})mm")
