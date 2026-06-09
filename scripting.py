import re
import numpy as np
from spatialiser import MultiSpeakerSpatialiser
import time
import main

def is_valid_float(s):
    """Check if string is a valid float."""
    try:
        float(s)
        return True
    except ValueError:
        return False


def parse_script(lines):
    """Parse a script file and return a list of action tuples."""
    actions = []
    global itd_exaggeration, ild_exponent, tone_duration

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#'):
            continue

        # Config assignment
        m = re.match(r'(\w+)\s*=\s*([0-9.]+)', line)
        if m:
            key, val = m.group(1).lower(), float(m.group(2))
            if key == 'itd_exaggeration':
                itd_exaggeration = val
            elif key == 'ild_exponent':
                ild_exponent = val
            elif key == 'tone_duration':
                tone_duration = val
            continue

        parts = line.split()
        cmd = parts[0].upper()

        if cmd == 'WAIT':
            try:
                actions.append(('WAIT', float(parts[1])))
            except (ValueError, IndexError):
                print(f"Warning: Invalid WAIT command: {line}")
                continue

        elif cmd == 'JUMP':
            try:
                coords = parts[1].split(',')
                if len(coords) != 2 or not all(is_valid_float(c) for c in coords):
                    print(f"Warning: Invalid JUMP coordinates: {line}")
                    continue
                x, y = map(float, coords)
                actions.append(('JUMP', np.array([x, y])))
            except (ValueError, IndexError):
                print(f"Warning: Invalid JUMP command: {line}")
                continue

        elif cmd == 'SOUND':
            try:
                coords = parts[1].split(',')
                if len(coords) != 2 or not all(is_valid_float(c) for c in coords):
                    print(f"Warning: Invalid SOUND coordinates: {line}")
                    continue
                pos = np.array([float(coords[0]), float(coords[1])])

                #freq_match = re.search(r'FREQ=([0-9.]+)', line)
                freq_match = re.search(r'FREQ=([0-9.,:]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)

                if not freq_match or not amp_match:
                    print(f"Warning: Missing FREQ or AMP in SOUND command: {line}")
                    continue

                freq_string = freq_match.group(1)
                ### New Here
                if ':' in freq_string:
                    freqs = []

                    for item in freq_string.split(','):
                        freq, weight = item.split(':')
                        freqs.append((float(freq), float(weight)))

                    freq = freqs
                else:
                    freq = float(freq_string)
                ###
                amp = float(amp_match.group(1))
                actions.append(('SOUND', pos, freq, amp))
            except (ValueError, IndexError):
                print(f"Warning: Invalid SOUND command: {line}")
                continue
        else:
            print(f"Warning: Unknown command: {cmd}")

    return actions


def execute(actions, with_visualization=False):
    """Execute a sequence of parsed actions."""
    # Use existing spatialiser if available, otherwise create one with warning
    if hasattr(main.generate_tactile_tone, 'spatialiser') and main.generate_tactile_tone.spatialiser:
        spatialiser = main.generate_tactile_tone.spatialiser
        print("Using existing spatialiser configuration")
    else:
        print("WARNING: No spatialiser found, creating default configuration")
        spatialiser = MultiSpeakerSpatialiser()
        main.generate_tactile_tone.spatialiser = spatialiser

    # Make sure we're not starting multiple streams
    if spatialiser.audio_engine.stream is None:
        spatialiser.start()

    for act in actions:
        cmd = act[0]

        if cmd == 'WAIT':
            time.sleep(act[1])

        elif cmd == 'SOUND':
            _, pos, freq, amp = act
            # Generate and play the sound
            #spatialiser.audio_engine.play_tone(pos, freq, amp)
            if isinstance(freq, list):
                spatialiser.audio_engine.play_weighted_tone(pos, freq, amp)
            else:
                spatialiser.audio_engine.play_tone(pos, freq, amp)



