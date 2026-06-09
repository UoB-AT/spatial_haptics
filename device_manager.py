import sounddevice as sd
import numpy as np


def list_audio_devices():
    """List all available audio output devices with their capabilities."""
    print("\n=== Available Audio Output Devices ===")

    try:
        devices = sd.query_devices()
        default_device = sd.default.device[1] if isinstance(sd.default.device, tuple) else sd.default.device

        print(f"System default output device: {default_device}")
        print(f"Total devices found: {len(devices)}")

        print("\n" + "=" * 80)
        print(f"{'ID':<3} {'Name':<45} {'Ch':<3} {'Rate':<7} {'Notes'}")
        print("-" * 80)

        suitable_devices = []

        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                name = device['name'][:45]  # Truncate long names
                channels = device['max_output_channels']
                rate = f"{device['default_samplerate']:.0f}Hz"

                # Build notes
                notes = []
                if i == default_device:
                    notes.append("DEFAULT")

                if channels >= 16:
                    notes.append("16+ CH")
                    suitable_devices.append(i)
                elif channels >= 4:
                    notes.append("4+ CH")
                elif channels >= 2:
                    notes.append("STEREO")

                # Check for professional audio keywords
                name_lower = device['name'].lower()
                pro_keywords = ['mchstreamer', 'tdm16', 'minidsp', 'mch', 'class compliant', 'usb audio', 'focusrite',
                                'behringer']
                for keyword in pro_keywords:
                    if keyword in name_lower:
                        notes.append("PROFESSIONAL")
                        break

                notes_str = " | ".join(notes)
                print(f"{i:<3} {name:<45} {channels:<3} {rate:<7} {notes_str}")

        if suitable_devices:
            print(f"\nDevices with 16+ channels (suitable for 4x4 grid): {suitable_devices}")

        return devices

    except Exception as e:
        print(f"Error listing devices: {e}")
        return []


def select_audio_device_interactive(required_channels=2):
    """Interactive device selection."""
    devices = list_audio_devices()

    if not devices:
        return None

    print(f"\nSelect audio device for {required_channels} channels:")

    # Show suitable devices
    suitable = []
    for i, device in enumerate(devices):
        if device['max_output_channels'] >= required_channels:
            suitable.append(i)

    if suitable:
        print(f"Recommended devices (>= {required_channels} channels): {suitable}")

    while True:
        try:
            choice = input(f"\nEnter device number (0-{len(devices) - 1}) or 'q' to quit: ").strip()

            if choice.lower() == 'q':
                return None

            device_id = int(choice)

            if 0 <= device_id < len(devices):
                device = devices[device_id]

                if device['max_output_channels'] < required_channels:
                    print(
                        f"Warning: Device only has {device['max_output_channels']} channels, need {required_channels}")
                    confirm = input("Continue anyway? (y/n): ").strip().lower()
                    if confirm != 'y':
                        continue

                print(f"Selected: {device['name']} ({device['max_output_channels']} channels)")
                return device_id
            else:
                print(f"Invalid device number. Must be 0-{len(devices) - 1}")

        except ValueError:
            print("Invalid input. Enter a number or 'q'")
        except KeyboardInterrupt:
            return None


def test_audio_device(device_id, channels=None, duration=2.0):
    """Test an audio device with a simple tone."""
    try:
        devices = sd.query_devices()
        if device_id >= len(devices):
            print(f"Error: Device {device_id} not found")
            return False

        device = devices[device_id]
        max_channels = device['max_output_channels']

        if max_channels == 0:
            print(f"Error: Device {device_id} has no output channels")
            return False

        # Determine test channels
        if channels is None:
            test_channels = min(max_channels, 16)  # Test up to 16 channels
        else:
            test_channels = min(channels, max_channels)

        print(f"Testing Device {device_id}: {device['name']}")
        print(f"Max channels: {max_channels}, Testing: {test_channels} channels")

        # Generate test tone
        sample_rate = 48000
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = 0.3 * np.sin(2 * np.pi * 440 * t)

        # Create multi-channel buffer
        buffer = np.zeros((len(tone), test_channels))
        buffer[:, 0] = tone  # Left channel
        if test_channels > 1:
            buffer[:, 1] = 0.3 * np.sin(2 * np.pi * 880 * t)  # Right channel (higher pitch)

        # Play through specified device
        sd.play(buffer, samplerate=sample_rate, device=device_id)
        sd.wait()

        print(f"✓ Device {device_id} test completed successfully")
        return True

    except Exception as e:
        print(f"✗ Device {device_id} test failed: {e}")
        return False


def find_mchstreamer_device():
    """Try to automatically find MCHStreamer or similar multi-channel device."""
    try:
        devices = sd.query_devices()

        # Look for devices with specific keywords and high channel counts
        mch_keywords = ['mchstreamer', 'tdm16', 'minidsp', 'mch', 'multichannel', 'tactile']

        candidates = []

        for i, device in enumerate(devices):
            if device['max_output_channels'] == 0:
                continue

            score = 0
            reasons = []

            # Perfect match: exactly 16 channels
            if device['max_output_channels'] == 16:
                score += 100
                reasons.append("16 channels (perfect match)")

            # Good match: high channel count
            elif device['max_output_channels'] >= 8:
                score += 50
                reasons.append(f"{device['max_output_channels']} channels (multi-channel)")

            # Check device name for keywords
            name_lower = device['name'].lower()

            for keyword in mch_keywords:
                if keyword in name_lower:
                    score += 150
                    reasons.append(f"keyword: {keyword}")
                    break

            # Sample rate preference (48kHz is ideal)
            if device['default_samplerate'] == 48000:
                score += 20
                reasons.append("48kHz sampling")

            if score > 0:
                candidates.append((score, i, device, reasons))

        # Sort by score (highest first)
        candidates.sort(reverse=True)

        if not candidates:
            print("No likely MCHStreamer/multi-channel devices found")
            return None

        print(f"Found {len(candidates)} potential candidates:")

        for j, (score, device_id, device, reasons) in enumerate(candidates[:5]):  # Show top 5
            print(f"{j + 1}. Device {device_id}: {device['name']}")
            print(f"   Score: {score}, Channels: {device['max_output_channels']}")
            print(f"   Reasons: {', '.join(reasons)}")

        best_device_id = candidates[0][1]
        return best_device_id

    except Exception as e:
        print(f"Error finding MCHStreamer device: {e}")
        return None

