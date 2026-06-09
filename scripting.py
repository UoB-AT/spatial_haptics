import re
import numpy as np
from spatialiser import MultiSpeakerSpatialiser
import time
import main

# === SCRIPT PARSING (INTEGRATED FROM ORIGINAL) ===
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

                freq_match = re.search(r'FREQ=([0-9.]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)

                if not freq_match or not amp_match:
                    print(f"Warning: Missing FREQ or AMP in SOUND command: {line}")
                    continue

                freq = float(freq_match.group(1))
                amp = float(amp_match.group(1))
                actions.append(('SOUND', pos, freq, amp))
            except (ValueError, IndexError):
                print(f"Warning: Invalid SOUND command: {line}")
                continue

        elif cmd == 'ARC':
            try:
                # Extract points (2 or 3 points)
                point_matches = re.findall(r'(-?[0-9.]+),(-?[0-9.]+)', line)

                if len(point_matches) < 2:
                    print(f"Warning: ARC requires at least 2 points: {line}")
                    continue

                if len(point_matches) > 3:
                    print(f"Warning: ARC accepts at most 3 points. Using first 3.")
                    point_matches = point_matches[:3]

                # Convert points to numpy arrays
                points = []
                for x_str, y_str in point_matches:
                    points.append(np.array([float(x_str), float(y_str)]))

                # Extract parameters
                duration_match = re.search(r'DURATION=([0-9.]+)', line)
                steps_match = re.search(r'STEPS=([0-9]+)', line)
                freq_match = re.search(r'FREQ=([0-9.]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)

                if not all([duration_match, steps_match, freq_match, amp_match]):
                    print(f"Warning: Missing parameters in ARC command: {line}")
                    continue

                duration = float(duration_match.group(1))
                steps = int(steps_match.group(1))
                freq = float(freq_match.group(1))
                amp = float(amp_match.group(1))

                # Check for MODE parameter
                mode_match = re.search(r'MODE=(\w+)', line)
                mode = mode_match.group(1).upper() if mode_match else 'STRAIGHT'

                actions.append(('ARC', points, duration, steps, freq, amp, mode))
            except (ValueError, IndexError) as e:
                print(f"Warning: Invalid ARC command: {line} - {e}")
                continue

        elif cmd == 'CIRCLE_SMOOTH':
            try:
                radius_match = re.search(r'RADIUS=([0-9.]+)', line)
                duration_match = re.search(r'DURATION=([0-9.]+)', line)
                steps_match = re.search(r'STEPS=([0-9]+)', line)
                freq_match = re.search(r'FREQ=([0-9.]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)

                if not all([radius_match, duration_match, steps_match, freq_match, amp_match]):
                    print(f"Warning: Missing parameters in CIRCLE_SMOOTH command: {line}")
                    continue

                radius = float(radius_match.group(1))
                duration = float(duration_match.group(1))
                steps = int(steps_match.group(1))
                freq = float(freq_match.group(1))
                amp = float(amp_match.group(1))

                actions.append(('CIRCLE_SMOOTH', radius, duration, steps, freq, amp))
            except (ValueError, IndexError):
                print(f"Warning: Invalid CIRCLE_SMOOTH command: {line}")
                continue

        elif cmd == 'FREQ_RAMP':
            try:
                # Extract position
                pos_match = re.search(r'POS=(-?[0-9.]+),(-?[0-9.]+)', line)

                # Extract parameters with regex
                start_freq_match = re.search(r'START_FREQ=([0-9.]+)', line)
                end_freq_match = re.search(r'END_FREQ=([0-9.]+)', line)
                duration_match = re.search(r'DURATION=([0-9.]+)', line)
                steps_match = re.search(r'STEPS=([0-9]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)

                if not pos_match:
                    print(f"Warning: Missing position in FREQ_RAMP command: {line}")
                    continue

                if not all([start_freq_match, end_freq_match, duration_match, steps_match, amp_match]):
                    print(f"Warning: Missing parameters in FREQ_RAMP command: {line}")
                    continue

                pos = np.array([float(pos_match.group(1)), float(pos_match.group(2))])
                start_freq = float(start_freq_match.group(1))
                end_freq = float(end_freq_match.group(1))
                duration = float(duration_match.group(1))
                steps = int(steps_match.group(1))
                amp = float(amp_match.group(1))

                actions.append(('FREQ_RAMP', pos, start_freq, end_freq, duration, steps, amp))
            except (ValueError, IndexError):
                print(f"Warning: Invalid FREQ_RAMP command: {line}")
                continue

        elif cmd == 'FREQ_RAMP_SMOOTH':
            try:
                # Extract position
                pos_match = re.search(r'POS=(-?[0-9.]+),(-?[0-9.]+)', line)

                # Extract parameters with regex
                start_freq_match = re.search(r'START_FREQ=([0-9.]+)', line)
                end_freq_match = re.search(r'END_FREQ=([0-9.]+)', line)
                duration_match = re.search(r'DURATION=([0-9.]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)

                if not pos_match:
                    print(f"Warning: Missing position in FREQ_RAMP_SMOOTH command: {line}")
                    continue

                if not all([start_freq_match, end_freq_match, duration_match, amp_match]):
                    print(f"Warning: Missing parameters in FREQ_RAMP_SMOOTH command: {line}")
                    continue

                pos = np.array([float(pos_match.group(1)), float(pos_match.group(2))])
                start_freq = float(start_freq_match.group(1))
                end_freq = float(end_freq_match.group(1))
                duration = float(duration_match.group(1))
                amp = float(amp_match.group(1))

                actions.append(('FREQ_RAMP_SMOOTH', pos, start_freq, end_freq, duration, amp))
            except (ValueError, IndexError):
                print(f"Warning: Invalid FREQ_RAMP_SMOOTH command: {line}")
                continue

        elif cmd == 'PATH_FREQ_RAMP':
            try:
                # Extract points (2 or 3 points)
                point_matches = re.findall(r'(-?[0-9.]+),(-?[0-9.]+)', line)

                if len(point_matches) < 2:
                    print(f"Warning: PATH_FREQ_RAMP requires at least 2 points: {line}")
                    continue

                if len(point_matches) > 3:
                    print(f"Warning: PATH_FREQ_RAMP accepts at most 3 points. Using first 3.")
                    point_matches = point_matches[:3]

                # Convert points to numpy arrays
                points = []
                for x_str, y_str in point_matches:
                    points.append(np.array([float(x_str), float(y_str)]))

                # Extract parameters
                start_freq_match = re.search(r'START_FREQ=([0-9.]+)', line)
                end_freq_match = re.search(r'END_FREQ=([0-9.]+)', line)
                duration_match = re.search(r'DURATION=([0-9.]+)', line)
                steps_match = re.search(r'STEPS=([0-9]+)', line)
                amp_match = re.search(r'AMP=([0-9.]+)', line)

                if not all([start_freq_match, end_freq_match, duration_match, steps_match, amp_match]):
                    print(f"Warning: Missing parameters in PATH_FREQ_RAMP command: {line}")
                    continue

                start_freq = float(start_freq_match.group(1))
                end_freq = float(end_freq_match.group(1))
                duration = float(duration_match.group(1))
                steps = int(steps_match.group(1))
                amp = float(amp_match.group(1))

                # Check for MODE parameter
                mode_match = re.search(r'MODE=(\w+)', line)
                mode = mode_match.group(1).upper() if mode_match else 'STRAIGHT'

                actions.append(('PATH_FREQ_RAMP', points, start_freq, end_freq, duration, steps, amp, mode))
            except (ValueError, IndexError) as e:
                print(f"Warning: Invalid PATH_FREQ_RAMP command: {line} - {e}")
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

    current_pos = np.array([0.0, 0.0])

    for act in actions:
        cmd = act[0]

        if cmd == 'WAIT':
            time.sleep(act[1])

        elif cmd == 'JUMP':
            current_pos = act[1]
            main.update_position(current_pos, {'type': 'JUMP'})

        elif cmd == 'SOUND':
            _, pos, freq, amp = act
            current_pos = pos
            main.update_position(current_pos, {'type': 'SOUND', 'freq': freq, 'amp': amp})

            # Generate and play the sound
            spatialiser.audio_engine.play_tone(pos, freq, amp)

        elif cmd == 'ARC':
            _, points, duration, steps, freq, amp, mode = act

            if steps <= 0:
                print("Warning: ARC with steps <= 0, skipping")
                continue

            # Calculate the time for each step
            step_time = duration / steps

            # Handle interpolation based on number of points and mode
            for i in range(steps):
                t = i / (steps - 1) if steps > 1 else 0

                if mode == 'CURVED' and len(points) == 3:
                    # Quadratic Bézier via midpoint
                    P0, Pm, P1 = points[0], points[1], points[2]
                    pos = (1 - t) ** 2 * P0 + 2 * (1 - t) * t * Pm + t ** 2 * P1
                else:
                    # Linear interpolation between first and last points
                    P0, P1 = points[0], points[-1]
                    pos = P0 * (1 - t) + P1 * t

                current_pos = pos
                main.update_position(current_pos, {'type': 'ARC', 'freq': freq, 'amp': amp})

                # Play sound
                spatialiser.audio_engine.play_tone(pos, freq, amp)

                if i < steps - 1:  # Don't sleep after the last point
                    time.sleep(step_time)

        elif cmd == 'CIRCLE_SMOOTH':
            _, radius, duration, steps, freq, amp = act

            # Generate the buffer
            buf = spatialiser.audio_engine.generate_circle_buffer(radius, duration, steps, freq, amp)

            # Start audio playback and visualization synchronously
            if with_visualization:
                import threading

                # Start audio playback in a separate thread
                def play_audio():
                    if spatialiser.audio_engine.stream:
                        spatialiser.audio_engine.stream.write(buf.astype('float32'))

                audio_thread = threading.Thread(target=play_audio)
                audio_thread.daemon = True
                audio_thread.start()

                # Update visualization in sync with audio
                start_time = time.time()
                vis_steps = min(steps, 200)  # Limit to reasonable number of updates

                for i in range(vis_steps):
                    # Calculate current position based on elapsed time
                    elapsed = time.time() - start_time
                    progress = min(1.0, elapsed / duration)

                    # Calculate position on circle
                    angle = 2 * np.pi * progress
                    x = radius * np.sin(angle)
                    y = radius * np.cos(angle)
                    pos = np.array([x, y])

                    main.update_position(pos, {'type': 'CIRCLE', 'freq': freq, 'amp': amp})

                    # Sleep for smooth animation
                    time.sleep(duration / vis_steps)

                # Wait for audio to complete
                audio_thread.join()

            else:
                # Without visualization, just play the audio
                if spatialiser.audio_engine.stream:
                    spatialiser.audio_engine.stream.write(buf.astype('float32'))

                    # Still need to wait for the duration
                    time.sleep(duration)

        elif cmd == 'FREQ_RAMP':
            _, pos, start_freq, end_freq, duration, steps, amp = act

            if steps <= 0:
                print("Warning: FREQ_RAMP with steps <= 0, skipping")
                continue

            # Calculate the time for each step
            step_time = duration / steps

            # Generate frequencies for each step
            for i in range(steps):
                t = i / (steps - 1) if steps > 1 else 0

                # Linear interpolation of frequency
                freq = start_freq * (1 - t) + end_freq * t

                current_pos = pos
                main.update_position(current_pos, {'type': 'FREQ_RAMP', 'freq': freq, 'amp': amp})

                # Play sound
                spatialiser.audio_engine.play_tone(pos, freq, amp)

                if i < steps - 1:  # Don't sleep after the last point
                    time.sleep(step_time)

        elif cmd == 'FREQ_RAMP_SMOOTH':
            _, pos, start_freq, end_freq, duration, amp = act

            # Generate a continuous buffer with smooth frequency ramping
            buf = spatialiser.audio_engine.generate_freq_ramp_buffer(pos, start_freq, end_freq, duration, amp)

            # Start audio playback and visualization synchronously
            if with_visualization:
                import threading

                # Start audio playback in a separate thread
                def play_audio():
                    if spatialiser.audio_engine.stream:
                        spatialiser.audio_engine.stream.write(buf.astype('float32'))

                audio_thread = threading.Thread(target=play_audio)
                audio_thread.daemon = True
                audio_thread.start()

                # Update visualization in sync with audio
                start_time = time.time()
                vis_steps = 100  # Reasonable number of updates

                for i in range(vis_steps):
                    # Calculate current frequency based on elapsed time
                    elapsed = time.time() - start_time
                    progress = min(1.0, elapsed / duration)

                    # Calculate current frequency
                    freq = start_freq + (end_freq - start_freq) * progress

                    main.update_position(pos, {'type': 'FREQ_RAMP_SMOOTH', 'freq': freq, 'amp': amp})

                    # Sleep for smooth animation
                    time.sleep(duration / vis_steps)

                # Wait for audio to complete
                audio_thread.join()

            else:
                # Without visualization, just play the audio
                if spatialiser.audio_engine.stream:
                    spatialiser.audio_engine.stream.write(buf.astype('float32'))

                    # Still need to wait for the duration
                    time.sleep(duration)

        elif cmd == 'PATH_FREQ_RAMP':
            _, points, start_freq, end_freq, duration, steps, amp, mode = act

            if steps <= 0:
                print("Warning: PATH_FREQ_RAMP with steps <= 0, skipping")
                continue

            # Generate a continuous buffer with both position and frequency changes
            buf, positions = spatialiser.audio_engine.generate_path_freq_ramp_buffer(
                points, mode, start_freq, end_freq, duration, steps, amp)

            # Start audio playback and visualization synchronously
            if with_visualization:
                import threading

                # Start audio playback in a separate thread
                def play_audio():
                    if spatialiser.audio_engine.stream:
                        spatialiser.audio_engine.stream.write(buf.astype('float32'))

                audio_thread = threading.Thread(target=play_audio)
                audio_thread.daemon = True
                audio_thread.start()

                # Update visualization in sync with audio
                start_time = time.time()
                vis_steps = min(100, len(positions) // 10)  # Reasonable number of updates

                for i in range(vis_steps):
                    # Calculate current position and frequency based on elapsed time
                    elapsed = time.time() - start_time
                    progress = min(1.0, elapsed / duration)

                    # Calculate position index
                    pos_idx = int(progress * (len(positions) - 1))
                    if pos_idx >= len(positions):
                        pos_idx = len(positions) - 1

                    pos = positions[pos_idx]
                    freq = start_freq + (end_freq - start_freq) * progress

                    main.update_position(pos, {'type': 'PATH_FREQ_RAMP', 'freq': freq, 'amp': amp})

                    # Sleep for smooth animation
                    time.sleep(duration / vis_steps)

                # Wait for audio to complete
                audio_thread.join()

            else:
                # Without visualization, just play the audio
                if spatialiser.audio_engine.stream:
                    spatialiser.audio_engine.stream.write(buf.astype('float32'))

                    # Still need to wait for the duration
                    time.sleep(duration)

    # Note: Don't automatically stop the spatialiser here to allow for reuse


def execute_with_visualization(actions):
    """Execute script with visualization support."""
    return execute(actions, with_visualization=True)



# === COMPATIBILITY FUNCTIONS (for original system) ===
# def set_visualizer_callback(callback):
#     """Set a callback function to be called when position changes."""
#     global visualizer_callback
#     visualizer_callback = callback
#
#
# def update_position(position, action=None):
#     """Update the current position and notify visualizer if callback exists."""
#     global current_position
#
#     with main.position_lock:
#         main.current_position = position.copy()
#
#     # Notify visualizer
#     if visualizer_callback:
#         visualizer_callback(position, action)
#
# def generate_tactile_tone(source_pos, freq, amp):
#     """Generate a tactile tone (compatibility with original system)."""
#     # Update position for visualization
#     update_position(source_pos, {'type': 'SOUND', 'freq': freq, 'amp': amp})
#
#     # Use the global spatialiser if available
#     if hasattr(generate_tactile_tone, 'spatialiser'):
#         return generate_tactile_tone.spatialiser.audio_engine.generate_tone(source_pos, freq, amp)
#     else:
#         # Fallback to simple stereo generation
#         N = int(tone_duration * main.sample_rate)
#         t = np.arange(N) / main.sample_rate
#         tone = amp * np.sin(2 * np.pi * freq * t)
#
#         # Simple stereo panning
#         pan = np.clip(source_pos[0] + 0.5, 0, 1)  # -0.5 to 0.5 -> 0 to 1
#         left = tone * (1 - pan)
#         right = tone * pan
#
#         return np.column_stack([left, right])
#
#
# def generate_circle_buffer(radius, duration, steps, freq, amp):
#     """Generate a seamless circular sweep buffer."""
#     if hasattr(generate_tactile_tone, 'spatialiser'):
#         return generate_tactile_tone.spatialiser.audio_engine.generate_circle_buffer(radius, duration, steps, freq, amp)
#     else:
#         # Fallback to simple stereo
#         N = int(duration * main.sample_rate)
#         t = np.arange(N) / main.sample_rate
#         left = amp * np.sin(2 * np.pi * freq * t)
#         right = amp * np.sin(2 * np.pi * freq * t)
#         return np.column_stack([left, right])




# === CONFIGURATION FILE GENERATORS ===
def create_example_configs():
    """Create example configuration files with corrected 0-based channel assignments."""

    # 1. Default 4x4 grid (40mm spacing) - FIXED CHANNELS
    with open('config_4x4_grid.txt', 'w') as f:
        f.write("""# 4x4 Tactile Grid Configuration
# 40mm spacing between speaker centers
# Optimized for tactile/haptic feedback
# CHANNELS START AT 0

config_name = 4x4_tactile_grid
method = tactile_grid

# Create 4x4 grid with 40mm spacing
GRID SIZE=4 SPACING=0.04 OFFSET=0.0,0.0

# This creates a 120mm x 120mm grid with speakers at:
# Row 0: (-0.060,-0.060), (-0.020,-0.060), (0.020,-0.060), (0.060,-0.060)
# Row 1: (-0.060,-0.020), (-0.020,-0.020), (0.020,-0.020), (0.060,-0.020)
# Row 2: (-0.060,0.020), (-0.020,0.020), (0.020,0.020), (0.060,0.020)
# Row 3: (-0.060,0.060), (-0.020,0.060), (0.020,0.060), (0.060,0.060)

# Channels are assigned as (0-based):
# CH0  CH1  CH2  CH3     (bottom row)
# CH4  CH5  CH6  CH7     
# CH8  CH9  CH10 CH11    
# CH12 CH13 CH14 CH15    (top row)
""")

    # 2. 2x2 test grid (4 channels) - FIXED CHANNELS
    with open('config_2x2_test.txt', 'w') as f:
        f.write("""# 2x2 Test Grid Configuration
# 40mm spacing for testing with limited channels
# CHANNELS START AT 0

config_name = 2x2_test_grid
method = tactile_grid

# Create 2x2 grid with 40mm spacing
GRID SIZE=2 SPACING=0.04 OFFSET=0.0,0.0

# This creates speakers at:
# (-0.020,-0.020), (0.020,-0.020)  (bottom row)
# (-0.020,0.020), (0.020,0.020)    (top row)

# Channels: CH0, CH1, CH2, CH3 (0-based)
""")

    # 3. 8-speaker circle - FIXED CHANNELS
    with open('config_octagon.txt', 'w') as f:
        f.write("""# Octagon Speaker Array
# 8 speakers in a circle for room audio
# CHANNELS START AT 0

config_name = octagon_room
method = vbap

# Create 8-speaker circle with 2m radius
CIRCLE COUNT=8 RADIUS=2.0 OFFSET=0.0,0.0

# Channels: CH0-CH7 (0-based)
""")

    # 4. Stereo pair - FIXED CHANNELS
    with open('config_stereo.txt', 'w') as f:
        f.write("""# Stereo Speaker Configuration
# Standard left/right speakers
# CHANNELS START AT 0

config_name = stereo_pair
method = itd_ild

# Left and right speakers (0-based channels)
SPEAKER LEFT  -0.5,0.0 CHANNEL=0 DESCRIPTION="Left speaker"
SPEAKER RIGHT  0.5,0.0 CHANNEL=1 DESCRIPTION="Right speaker"
""")

    # 5. 8x8 high-resolution grid - FIXED CHANNELS
    with open('config_8x8_grid.txt', 'w') as f:
        f.write("""# 8x8 High-Resolution Tactile Grid
# 20mm spacing for detailed tactile feedback
# CHANNELS START AT 0

config_name = 8x8_tactile_grid
method = nearest_neighbor

# Create 8x8 grid with 20mm spacing
GRID SIZE=8 SPACING=0.02 OFFSET=0.0,0.0

# This creates a 140mm x 140mm grid with 64 speakers
# Channels: CH0-CH63 (0-based)
""")

    # 6. Development configuration - FIXED CHANNELS
    with open('config_development.txt', 'w') as f:
        f.write("""# Development Configuration
# Minimal setup for testing and development
# CHANNELS START AT 0

config_name = development
method = distance_pan

# Just 4 speakers for easy testing (0-based channels)
SPEAKER TL -0.02,0.02 CHANNEL=0 DESCRIPTION="Top left"
SPEAKER TR  0.02,0.02 CHANNEL=1 DESCRIPTION="Top right"
SPEAKER BL -0.02,-0.02 CHANNEL=2 DESCRIPTION="Bottom left"
SPEAKER BR  0.02,-0.02 CHANNEL=3 DESCRIPTION="Bottom right"
""")

    print("Created example configuration files with 0-based channel assignments:")
    print("  - config_4x4_grid.txt (default 4x4 tactile grid, 40mm spacing, CH0-CH15)")
    print("  - config_2x2_test.txt (2x2 test grid, CH0-CH3)")
    print("  - config_octagon.txt (8-speaker circle, CH0-CH7)")
    print("  - config_stereo.txt (standard stereo, CH0-CH1)")
    print("  - config_8x8_grid.txt (high-resolution 8x8 grid, CH0-CH63)")
    print("  - config_development.txt (development/debug, CH0-CH3)")

