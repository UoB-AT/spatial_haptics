import argparse
from speaker.scripting import *
import numpy as np
from speaker.spatialiser import MultiSpeakerSpatialiser
from acquire.record import record
import threading
import time


sample_rate = 48000
tone_duration = 0.1
itd_exaggeration = 1.0
ild_exponent = 1.0

def generate_tactile_tone(source_pos, freq, amp):
    """Generate a tactile tone (compatibility with original system)."""
    # Update position for visualization

    # Use the global spatialiser if available
    if hasattr(generate_tactile_tone, 'spatialiser'):
        return generate_tactile_tone.spatialiser.audio_engine.generate_tone(source_pos, freq, amp)
    else:
        # Fallback to simple stereo generation
        N = int(tone_duration * sample_rate)
        t = np.arange(N) / sample_rate
        tone = amp * np.sin(2 * np.pi * freq * t)

        # Simple stereo panning
        pan = np.clip(source_pos[0] + 0.5, 0, 1)
        left = tone * (1 - pan)
        right = tone * pan

        return np.column_stack([left, right])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Multi-Speaker Spatialiser with FIXED Device Selection')
    parser.add_argument('script', nargs='?', help='Tactile script file to execute')
    parser.add_argument('--config', help='Speaker configuration file')
    parser.add_argument('--device', type=int, help='Audio device ID (use --list-devices to see options)')
    parser.add_argument("--filename", type=str, default= "data/recording.wav", help="Filename of saved recording")
    parser.add_argument("--duration", type=float, default=10, help="Total duration of recording in seconds")
    parser.add_argument("--samplerate", type=float, default=96000, help="sampling rate of recording in Hz (96000 by default)")
    args = parser.parse_args()

    device_id = args.device

    if args.script:
        # Execute a tactile script
        spatialiser = MultiSpeakerSpatialiser(args.config, device_id)
        generate_tactile_tone.spatialiser = spatialiser

        try:
            with open(args.script, 'r') as f:
                lines = f.read().splitlines()

            actions = parse_script(lines, spatialiser)
            print(f"Executing script: {args.script}")
            print(f"Using configuration: {spatialiser.speaker_config.config_name}")
            if device_id is not None:
                print(f"Using audio device: {device_id}")

            record_thread = threading.Thread(target=record, args=(args.duration, args.filename, args.samplerate))
            print("✓ Start Recording")
            record_thread.start()
            time.sleep(0.5) # wait 1 s and then start playing the audio
            execute(actions, spatialiser)
            print("✓ Playback finished")
            print("✓ Waiting for recording to finish")
            record_thread.join()
            print("✓ Recording finished")

        except Exception as e:
            print(f"Error executing script: {e}")
        finally:
            try:
                spatialiser.stop()
            except:
                pass
