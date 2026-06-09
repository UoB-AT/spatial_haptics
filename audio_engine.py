import threading
import sounddevice as sd
import numpy as np
from spatialisation import SpatializationEngine


class MultiSpeakerAudioEngine:
    def __init__(self, speaker_config, sample_rate=48000, device_id=None):
        self.config = speaker_config
        self.sample_rate = sample_rate
        self.device_id = device_id  # Store preferred device ID
        self.spat_engine = SpatializationEngine(speaker_config)

        # Track if user specified a device (for strict enforcement)
        self._user_specified_device = device_id is not None

        # Audio parameters
        self.tone_duration = 0.1
        self.fade_duration = 0.05
        self.fade_len = int(self.fade_duration * sample_rate)

        # Initialize audio stream
        self.num_channels = self.config.get_num_channels()
        self.stream = None

        # Threading lock for thread-safe operation
        self.lock = threading.Lock()

        print(f"Audio engine initialized: {self.num_channels} channels (0-{self.num_channels - 1})")
        if self.device_id is not None:
            print(f"User-specified device: {self.device_id} (strict mode)")
        else:
            print("No device specified, will auto-select suitable device")

    def validate_device_selection(self):
        """Validate that the specified device exists and has enough channels."""
        if self.device_id is None:
            return True  # Auto-selection will handle this

        try:
            devices = sd.query_devices()

            if self.device_id >= len(devices) or self.device_id < 0:
                print(f"ERROR: Device {self.device_id} does not exist (valid range: 0-{len(devices) - 1})")
                return False

            device = devices[self.device_id]

            if device['max_output_channels'] == 0:
                print(f"ERROR: Device {self.device_id} ({device['name']}) is not an output device")
                return False

            if device['max_output_channels'] < self.num_channels:
                print(
                    f"WARNING: Device {self.device_id} ({device['name']}) only has {device['max_output_channels']} channels")
                print(f"Your configuration needs {self.num_channels} channels")
                response = input("Continue anyway? (y/n): ").strip().lower()
                if response != 'y':
                    return False

            print(f"Device {self.device_id} validated: {device['name']} ({device['max_output_channels']} channels)")
            return True

        except Exception as e:
            print(f"ERROR: Cannot validate device {self.device_id}: {e}")
            return False

    def set_parameters(self, **kwargs):
        """Set audio parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                if key == 'fade_duration':
                    self.fade_len = int(value * self.sample_rate)
            elif hasattr(self.spat_engine, key):
                self.spat_engine.set_parameters(**{key: value})

    def start_stream(self):
        """Start the audio output stream with STRICT device selection - FIXED VERSION."""
        with self.lock:
            if self.stream is None:
                # If user specified a device, ONLY try that device
                if self.device_id is not None:
                    print(f"Attempting to use specified device {self.device_id}...")
                    if self._try_device(self.device_id):
                        return
                    else:
                        # User's device failed - don't fallback, tell them
                        print(f"ERROR: Cannot use specified device {self.device_id}")
                        print("Use --list-devices to see available devices")
                        print("Use --test-device ID to test a specific device")
                        print("Use --select-device for interactive selection")
                        self.stream = None
                        return

                # No device specified by user - try defaults and auto-select
                print("No device specified, trying default device...")
                if self._try_device(None):
                    return

                # Default failed, auto-select suitable device
                print("Default device failed, searching for suitable device...")
                if self._auto_select_device():
                    return

                # Complete failure
                print("No suitable audio device found.")
                print("Use --list-devices to see available devices")
                print("Use --device ID to specify a device")
                self.stream = None

    # SIMPLE FIX: Add this method to MultiSpeakerAudioEngine class in multispeaker_main.py

    def _try_device(self, device_id):
        """Try to start stream with specific device - MCHSTREAMER WINDOWS FIX."""
        try:
            device_name = "default"
            if device_id is not None:
                devices = sd.query_devices()
                if 0 <= device_id < len(devices):
                    device = devices[device_id]
                    device_name = device['name']
                    available_channels = device['max_output_channels']

                    # MCHSTREAMER FIX: Try WASAPI for MCHStreamer devices
                    if 'mchstreamer' in device_name.lower() or 'mch' in device_name.lower():
                        print(f"MCHStreamer device detected, trying WASAPI API...")
                        try:
                            # Find WASAPI host API
                            host_apis = sd.query_hostapis()
                            wasapi_hostapi = None
                            for i, api in enumerate(host_apis):
                                if 'WASAPI' in api['name']:
                                    wasapi_hostapi = i
                                    break

                            if wasapi_hostapi is not None:
                                self.stream = sd.OutputStream(
                                    samplerate=self.sample_rate,
                                    channels=self.num_channels,
                                    dtype='float32',
                                    blocksize=1024,
                                    device=device_id,
                                    hostapi=wasapi_hostapi  # Force WASAPI
                                )
                                self.stream.start()
                                print(
                                    f"✓ MCHStreamer WASAPI: {device_name} ({self.num_channels} channels at {self.sample_rate}Hz)")
                                return True
                        except Exception as wasapi_error:
                            print(f"WASAPI failed: {wasapi_error}, trying default...")

                    # Check if device has enough channels
                    if available_channels < self.num_channels:
                        print(
                            f"WARNING: Device {device_id} ({device_name}) only has {available_channels} channels, need {self.num_channels}")
                else:
                    print(f"ERROR: Invalid device ID {device_id} (valid range: 0-{len(devices) - 1})")
                    return False

            # Default method
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.num_channels,
                dtype='float32',
                blocksize=1024,
                device=device_id
            )
            self.stream.start()
            print(f"✓ Audio stream started: {device_name} ({self.num_channels} channels at {self.sample_rate}Hz)")
            return True

        except Exception as e:
            if device_id is not None:
                print(f"✗ Device {device_id} ({device_name}) failed: {e}")

                # MCHSTREAMER HELPFUL MESSAGE
                if 'mchstreamer' in device_name.lower() and 'WDM-KS' in str(e):
                    print(f"💡 MCHStreamer Windows fix: Try using device 11 instead")
                    print(f"   Command: python multispeaker_main.py --device 11")
            else:
                print(f"✗ Default device failed: {e}")
            return False

    def _auto_select_device(self):
        """Automatically select the best available device - ONLY if no device was specified by user."""
        # If user specified a device, we should NEVER auto-select
        if self._user_specified_device:
            return False

        try:
            devices = sd.query_devices()

            # First try: exact channel match
            for i, device in enumerate(devices):
                if device['max_output_channels'] >= self.num_channels:
                    print(f"Auto-trying device {i}: {device['name']} ({device['max_output_channels']} channels)")
                    if self._try_device(i):
                        return True

            # Second try: any multi-channel device
            for i, device in enumerate(devices):
                if device['max_output_channels'] >= 2:
                    print(
                        f"Auto-trying fallback device {i}: {device['name']} ({device['max_output_channels']} channels)")
                    if self._try_device(i):
                        print(f"Warning: Using {device['max_output_channels']} channels instead of {self.num_channels}")
                        return True

            return False

        except Exception as e:
            print(f"Auto-selection failed: {e}")
            return False

    def stop_stream(self):
        """Stop the audio output stream."""
        with self.lock:
            if self.stream is not None:
                try:
                    self.stream.stop()
                    self.stream.close()
                    self.stream = None
                    print("Audio stream stopped")
                except Exception as e:
                    print(f"Error stopping audio stream: {e}")

    def __del__(self):
        """Cleanup when audio engine is destroyed."""
        try:
            self.stop_stream()
        except:
            pass  # Ignore errors during cleanup

    def generate_tone(self, source_pos, freq, amp):
        """Generate a spatialized tone for all speakers with proper 0-based channel mapping."""
        # Calculate gains and delays for all speakers
        gains, delays = self.spat_engine.calculate_gains_delays(source_pos)

        # Generate the base tone
        N = int(self.tone_duration * self.sample_rate)
        t = np.arange(N) / self.sample_rate

        # Create multi-channel output - ENSURE CORRECT CHANNEL COUNT
        output = np.zeros((N, self.num_channels))

        # Apply fade in/out window
        window = np.ones(N)
        if N > self.fade_len * 2:
            ramp = 0.5 * (1 - np.cos(np.pi * np.arange(self.fade_len) / self.fade_len))
            window[:self.fade_len] = ramp
            window[-self.fade_len:] = ramp[::-1]

        for i, speaker in enumerate(self.config.speakers):
            channel = speaker['channel']
            gain = gains[i]
            delay = delays[i]

            if gain > 0.001:  # Only process if significant gain
                # Apply delay (simplified - just phase shift for now)
                if delay != 0:
                    tone = amp * gain * np.sin(2 * np.pi * freq * (t - delay))
                else:
                    tone = amp * gain * np.sin(2 * np.pi * freq * t)

                # Apply window
                tone *= window

                # CRITICAL: Ensure we don't exceed channel count and use 0-based indexing
                if 0 <= channel < self.num_channels:
                    output[:, channel] = tone
                else:
                    print(
                        f"WARNING: Speaker {speaker['id']} channel {channel} exceeds available channels (0-{self.num_channels - 1})")

        return output

    def play_tone(self, source_pos, freq, amp):
        """Play a tone at the specified position."""
        # Always generate the buffer first
        buffer = self.generate_tone(source_pos, freq, amp)

        if self.stream is None:
            self.start_stream()

        if self.stream is not None:
            try:
                self.stream.write(buffer.astype('float32'))
            except Exception as e:
                print(f"Error writing to audio stream: {e}")
        return buffer
