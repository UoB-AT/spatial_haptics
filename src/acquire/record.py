import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np


def record(duration, filename, samplerate=48000):
    device_id = None
    for i, dev in enumerate(sd.query_devices()):
        if "H4" in dev["name"]:
            device_id = i
            print(f"✓ Found recorder: {dev['name']}")
            break

    if device_id is None:
        print("✗ Zoom H4 not connected. Recording aborted.")
        return

    # Force 48000Hz to prevent the Zoom interface from locking up
    native_sr = 48000
    total_channels = 1

    print(f"✓ Zoom recording initialized at {native_sr}Hz...")
    audio = sd.rec(
        int(duration * native_sr),
        samplerate=native_sr,
        channels=total_channels,
        device=device_id
    )
    sd.wait()

    write(filename, native_sr, audio)
    print(f"✓ Recording successfully saved to {filename}")



