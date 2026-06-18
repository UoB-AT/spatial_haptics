import re
import numpy as np
import time



def is_valid_float(s):
    """Check if string is a valid float."""
    try:
        float(s)
        return True
    except ValueError:
        return False


def parse_script(lines, spatialiser=None):
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
                # if hasattr(main, 'generate_tactile_tone') and hasattr(main.generate_tactile_tone, 'spatialiser'):
                    # main.generate_tactile_tone.spatialiser.set_parameters(tone_duration=val)
                if spatialiser is not None:
                    spatialiser.set_parameters(
                        tone_duration=val
                    )
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
                freq_match = re.search(r'FREQ=([0-9.,:]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)
                duration_match = re.search(r'DURATION=([0-9.]+)', line)

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
                duration = (
                    float(duration_match.group(1))
                    if duration_match
                    else None
                )
                actions.append(('SOUND', pos, freq, amp, duration))
            except (ValueError, IndexError):
                print(f"Warning: Invalid SOUND command: {line}")
                continue
        elif cmd == 'CHANNEL':
            try:
                channel = int(parts[1])
                freq_match = re.search(r'FREQ=([0-9.,:]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)
                duration_match = re.search(r'DURATION=([0-9.]+)', line)  # Look for duration

                freq_string = freq_match.group(1)
                freqs = []
                for item in freq_string.split(','):
                    freq, weight = item.split(':')
                    freqs.append((float(freq), float(weight)))

                amp = float(amp_match.group(1))
                duration = float(duration_match.group(1)) if duration_match else None
                actions.append(('CHANNEL', channel, freqs, amp, duration))
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Invalid CHANNEL syntax block: {line}. Error: {e}")
                continue
        elif cmd == 'CHANNELS':
            try:
                channels = [int(ch) for ch in parts[1].split(',')]
                freq_match = re.search(r'FREQ=([0-9.,:]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)
                duration_match = re.search(r'DURATION=([0-9.]+)', line)
                freq_string = freq_match.group(1)

                freqs = []

                for item in freq_string.split(','):
                    freq, weight = item.split(':')
                    freqs.append((float(freq), float(weight)))
                amp = float(amp_match.group(1))
                duration = (
                    float(duration_match.group(1))
                    if duration_match
                    else None
                )
                actions.append(('CHANNELS', channels, freqs, amp, duration))
            except Exception as e:
                print( f"Warning: Invalid CHANNELS syntax: {e}")

        elif cmd == 'MULTI':
            try:
                amp_match = re.search(r'AMP=([0-9.]+)', line)
                duration_match = re.search(r'DURATION=([0-9.]+)', line)
                amp = float(amp_match.group(1))
                duration = float(duration_match.group(1))
                assignments = {}
                matches = re.findall(r'CH(\d+)=([0-9.,:]+)', line)
                for ch_str, freq_string in matches:
                    channel = int(ch_str)
                    freqs = []
                    for item in freq_string.split(','):
                        freq, weight = item.split(':')
                        freqs.append((float(freq), float(weight)))
                    assignments[channel] = freqs
                actions.append(('MULTI', assignments, amp, duration))
            except Exception as e:
                print(f"MULTI parse error: {e}")

    return actions


def execute(actions, spatialiser):
    """Execute a sequence of parsed actions."""
    if spatialiser.audio_engine.stream is None:
        spatialiser.start()

    for act in actions:
        cmd = act[0]

        if cmd == 'WAIT':
            time.sleep(act[1])

        elif cmd == 'SOUND':
            _, pos, freq, amp, duration = act
            old_duration = spatialiser.audio_engine.tone_duration
            if duration is not None:
                spatialiser.audio_engine.tone_duration = duration
            try:
                print("Duration before play:", spatialiser.audio_engine.tone_duration)
                if isinstance(freq, list):
                    buffer = spatialiser.audio_engine.play_weighted_tone(pos, freq, amp)
                    tone_type = "weighted"
                else:
                    buffer = spatialiser.audio_engine.play_tone(pos, freq, amp)
                    tone_type = "standard"
                #time.sleep(spatialiser.audio_engine.tone_duration)

                #timestamp = int(time.time())
                #txt_filename = f"output/audio_output_{tone_type}_{timestamp}.txt"
                # np.savetxt(txt_filename, buffer, fmt='%.6f', delimiter=',')
                #print(f"✓ Audio array saved to text file: {txt_filename}")
            finally:
                spatialiser.audio_engine.tone_duration = old_duration

        elif cmd == 'CHANNEL':
            _, channel, freqs, amp, duration = act
            old_duration = spatialiser.audio_engine.tone_duration

            if duration is not None:
                spatialiser.audio_engine.tone_duration = duration
            try:
                buffer = spatialiser.audio_engine.play_direct_channel(
                    channel,
                    freqs,
                    amp
                )

                #timestamp = int(time.time())
                #txt_filename = f"output/audio_output_channel_{timestamp}.txt"
                #np.savetxt(txt_filename, buffer, fmt='%.6f', delimiter=',')
            finally:
                spatialiser.audio_engine.tone_duration = old_duration

        elif cmd == 'CHANNELS':
            _, channels, freqs, amp, duration = act
            old_duration = spatialiser.audio_engine.tone_duration
            if duration is not None:
                spatialiser.audio_engine.tone_duration = duration
            try:
                buffer = (spatialiser.audio_engine.play_multi_channel(channels, freqs, amp))
            finally:
                spatialiser.audio_engine.tone_duration = old_duration

        elif cmd == 'MULTI':
            _, assignments, amp, duration = act
            old_duration = (spatialiser.audio_engine.tone_duration)
            if duration is not None:
                spatialiser.audio_engine.tone_duration = duration
            try:
                spatialiser.audio_engine.play_multi_independent(assignments, amp)
            finally:
                spatialiser.audio_engine.tone_duration = old_duration