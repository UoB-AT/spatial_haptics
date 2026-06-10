import argparse
from scripting import *
import numpy as np


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
    args = parser.parse_args()


    device_id = args.device

    if args.script:
        # Execute a tactile script
        spatialiser = MultiSpeakerSpatialiser(args.config, device_id)

        # Set the global spatialiser BEFORE any execute calls
        generate_tactile_tone.spatialiser = spatialiser

        try:
            with open(args.script, 'r') as f:
                lines = f.read().splitlines()

            actions = parse_script(lines)
            print(f"Executing script: {args.script}")
            print(f"Actions: {len(actions)}")
            print(f"Using configuration: {spatialiser.speaker_config.config_name}")
            if device_id is not None:
                print(f"Using audio device: {device_id}")

            execute(actions)

        except Exception as e:
            print(f"Error executing script: {e}")
        finally:
            try:
                spatialiser.stop()
            except:
                pass
