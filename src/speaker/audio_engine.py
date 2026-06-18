import threading
import sounddevice as sd
import numpy as np
from .spatialisation import SpatializationEngine


class MultiSpeakerAudioEngine:
    def __init__(self, speaker_config, sample_rate=48000, device_id=None):
        # sample rate (not sure if I should change this as well)
        self.config = speaker_config
        self.sample_rate = sample_rate
        self.device_id = device_id  # Store preferred device ID
        self.spat_engine = SpatializationEngine(speaker_config)

        # Track if user specified a device (for strict enforcement)
        self._user_specified_device = device_id is not None

        # Audio parameters
        self.tone_duration = 0.1 # here needs to change (should not set 0.1 by default)
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

    def set_parameters(self, **kwargs):
        """Allow external scripts to update the tone_duration."""
        if 'tone_duration' in kwargs:
            self.tone_duration = float(kwargs['tone_duration'])
            print(f"✓ Audio Engine: tone_duration updated to {self.tone_duration}s")

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
        """Start the PortAudio output stream cleanly."""
        with self.lock:
            if self.stream is not None:
                return  # Stream is already active

            try:
                devices = sd.query_devices()
            except Exception as e:
                print(f"Error querying audio devices: {e}")
                return

            # Case A: A strict device ID was explicitly passed via CLI (--device X)
            if self.device_id is not None:
                try:
                    dev_info = devices[self.device_id]
                    device_name = dev_info.get('name', 'Unknown Device')

                    # Pass ALL 3 required arguments
                    success = self._try_device(self.device_id, device_name, devices)
                    if success:
                        return
                except IndexError:
                    print(f"Error: Specified device ID {self.device_id} is out of bounds.")

            # Case B: No device specified or explicit selection failed; auto-detect
            print("Searching for a suitable Core Audio/MCHStreamer device...")
            for idx, dev in enumerate(devices):
                # Target the MCHStreamer or matching high-channel layout
                if 'mchstreamer' in dev['name'].lower() or 'mch' in dev['name'].lower():
                    # Pass ALL 3 required arguments here too
                    success = self._try_device(idx, dev['name'], devices)
                    if success:
                        self.device_id = idx  # Save it for future reference
                        return

            # Case C: Hard fallback to system default output if no target hardware is auto-detected
            try:
                default_id = sd.default.device[1]  # Default output index
                default_name = devices[default_id]['name']
                print(f"Falling back to default system device: {default_name}")

                # Pass ALL 3 required arguments
                self._try_device(default_id, default_name, devices)
                self.device_id = default_id
            except Exception as fallback_err:
                print(f"Critical: All stream initialization paths failed: {fallback_err}")

    # SIMPLE FIX: Add this method to MultiSpeakerAudioEngine class in multispeaker_main.py
    def _try_device(self, device_id, device_name, devices):
        """Internal helper to attempt opening a stream on a specific device."""
        try:
            # Check if this is an MCHStreamer device (Core Audio / WASAPI)
            if 'mchstreamer' in device_name.lower() or 'mch' in device_name.lower():
                print(f"MCHStreamer detected! Applying specific hardware channel mapping...")
                self.stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=self.num_channels,  # Strict 16 channels
                    dtype='float32',
                    blocksize=1024,
                    device=device_id
                )
                self.stream.start()
                print(f"✓ Audio stream successfully locked: {device_name} (Device {device_id})")
                return True
            # Standard fallback for standard stereo outputs (like MacBook Speakers)
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
            print(f"✗ Device {device_id} failed: {e}")
            self.stream = None
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

    """ NEW ADDITION"""

    def generate_weighted_tone(self, source_pos, freqs_and_weights, amp):
        N = int(self.tone_duration * self.sample_rate)
        t = np.arange(N) / self.sample_rate
        tone = np.zeros(N)

        for freq, weight in freqs_and_weights:
            tone += weight * np.sin(2 * np.pi * freq * t)

        # Normalise
        peak = np.max(np.abs(tone))
        if peak > 0:
            tone /= peak

        tone *= amp

        gains, delays = self.spat_engine.calculate_gains_delays(source_pos)
        output = np.zeros((N, self.num_channels))

        for i, speaker in enumerate(self.config.speakers):
            channel = speaker['channel']

            if gains[i] > 0.001:
                output[:, channel] = tone * gains[i]
        return output

    def generate_direct_channel_tone(self, channel, freqs_and_weights, amp):
        N = int(self.tone_duration * self.sample_rate)
        t = np.arange(N) / self.sample_rate
        tone = np.zeros(N)
        for freq, weight in freqs_and_weights:
            tone += weight * np.sin(2 * np.pi * freq * t)
        peak = np.max(np.abs(tone))
        if peak > 0:
            tone /= peak
        tone *= amp
        output = np.zeros((N, self.num_channels))
        # channel argument is 1-based
        output[:, channel - 1] = tone
        return output

    def play_tone(self, source_pos, freq, amp):
        buffer = self.generate_tone(source_pos, freq, amp)

        # FIX: Ensure stream is started safely
        if self.stream is None:
            self.start_stream()

        # Give PortAudio a split-second to bind if it was just created
        if self.stream is None:
            import time
            time.sleep(0.05)

        if self.stream is not None:
            try:
                self.stream.write(buffer.astype('float32'))
            except Exception as e:
                print(f"Error writing to audio stream: {e}")
        else:
            print("✗ Error: Could not write audio data because stream failed to initialize.")
        return buffer

    def play_weighted_tone(self, source_pos, freqs_and_weights, amp):
        buffer = self.generate_weighted_tone(
            source_pos,
            freqs_and_weights,
            amp
        )

        # FIX: Ensure stream is started safely
        if self.stream is None:
            self.start_stream()

        if self.stream is None:
            import time
            time.sleep(0.05)

        if self.stream is not None:
            try:
                self.stream.write(buffer.astype('float32'))
            except Exception as e:
                print(f"Error writing to audio stream: {e}")
        else:
            print("✗ Error: Could not write audio data because stream failed to initialize.")
        return buffer

    def generate_multi_channel_tone(self, channels, freqs_and_weights, amp):
        N = int(self.tone_duration * self.sample_rate)
        t = np.arange(N) / self.sample_rate
        tone = np.zeros(N)
        for freq, weight in freqs_and_weights:
            tone += weight * np.sin(2 * np.pi * freq * t)
        peak = np.max(np.abs(tone))
        if peak > 0:
            tone /= peak
        tone *= amp
        output = np.zeros((N, self.num_channels))
        for ch in channels:
            output[:, ch - 1] = tone
        return output

    def generate_multi_independent(self, assignments, amp):
        N = int(self.tone_duration * self.sample_rate)
        t = np.arange(N) / self.sample_rate
        output = np.zeros((N, self.num_channels))
        for channel, freqs in assignments.items():
            tone = np.zeros(N)
            for freq, weight in freqs:
                tone += (weight * np.sin(2*np.pi*freq*t))
            peak = np.max(np.abs(tone))
            if peak > 0:
                tone /= peak
            tone *= amp
            output[:, channel - 1] = tone
        return output

    def play_direct_channel(self, channel, freqs_and_weights, amp):
        buffer = self.generate_direct_channel_tone(
            channel,
            freqs_and_weights,
            amp
        )

        if self.stream is None:
            self.start_stream()

        if self.stream is None:
            import time
            time.sleep(0.05)

        if self.stream is not None:
            try:
                self.stream.write(buffer.astype('float32'))
            except Exception as e:
                print(f"Error writing to audio stream: {e}")
        else:
            print("✗ Error: Could not write audio data because stream failed to initialize.")
        return buffer

    def play_multi_channel(self, channels, freqs_and_weights, amp):
        buffer = self.generate_multi_channel_tone(
            channels,
            freqs_and_weights,
            amp
        )
        if self.stream is None:
            self.start_stream()
        self.stream.write(buffer.astype('float32'))
        return buffer

    def play_multi_independent(self, assignments, amp):
        buffer = self.generate_multi_independent(assignments, amp)
        if self.stream is None:
            self.start_stream()
        self.stream.write(buffer.astype('float32'))
        return buffer