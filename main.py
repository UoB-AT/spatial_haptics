import argparse
import time
import os
from spatialiser import MultiSpeakerSpatialiser
from device_manager import (
    list_audio_devices,
    test_audio_device,
    select_audio_device_interactive,
    find_mchstreamer_device
)
from scripting import *
from config import SpeakerConfig
import threading

# === GLOBAL PARAMETERS (for compatibility with original system) ===
sample_rate = 48000
tone_duration = 0.1
itd_exaggeration = 1.0
ild_exponent = 1.0
current_position = np.array([0.0, 0.0])
visualizer_callback = None
position_lock = threading.Lock()

# === COMPATIBILITY FUNCTIONS (Inside main.py) ===

def set_visualizer_callback(callback):
    """Set a callback function to be called when position changes."""
    global visualizer_callback
    visualizer_callback = callback


def update_position(position, action=None):
    """Update the current position and notify visualizer if callback exists."""
    global current_position

    with position_lock:  # No 'main.' needed here since we are inside main.py
        current_position = position.copy()

    # Notify visualizer
    if visualizer_callback:
        visualizer_callback(position, action)


def generate_tactile_tone(source_pos, freq, amp):
    """Generate a tactile tone (compatibility with original system)."""
    # Update position for visualization
    update_position(source_pos, {'type': 'SOUND', 'freq': freq, 'amp': amp})

    # Use the global spatialiser if available
    if hasattr(generate_tactile_tone, 'spatialiser'):
        return generate_tactile_tone.spatialiser.audio_engine.generate_tone(source_pos, freq, amp)
    else:
        # Fallback to simple stereo generation
        N = int(tone_duration * sample_rate)
        t = np.arange(N) / sample_rate
        tone = amp * np.sin(2 * np.pi * freq * t)

        # Simple stereo panning
        pan = np.clip(source_pos[0] + 0.5, 0, 1)  # -0.5 to 0.5 -> 0 to 1
        left = tone * (1 - pan)
        right = tone * pan

        return np.column_stack([left, right])


def generate_circle_buffer(radius, duration, steps, freq, amp):
    """Generate a seamless circular sweep buffer."""
    if hasattr(generate_tactile_tone, 'spatialiser'):
        return generate_tactile_tone.spatialiser.audio_engine.generate_circle_buffer(radius, duration, steps, freq, amp)
    else:
        # Fallback to simple stereo
        N = int(duration * sample_rate)
        t = np.arange(N) / sample_rate
        left = amp * np.sin(2 * np.pi * freq * t)
        right = amp * np.sin(2 * np.pi * freq * t)
        return np.column_stack([left, right])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Multi-Speaker Spatialiser with FIXED Device Selection')
    parser.add_argument('script', nargs='?', help='Tactile script file to execute')
    parser.add_argument('--config', help='Speaker configuration file')
    parser.add_argument('--device', type=int, help='Audio device ID (use --list-devices to see options)')
    parser.add_argument('--list-devices', action='store_true', help='List available audio devices and exit')
    parser.add_argument('--select-device', action='store_true', help='Interactively select audio device')
    parser.add_argument('--find-device', action='store_true', help='Auto-find MCHStreamer or similar device')
    parser.add_argument('--test-device', type=int, help='Test specific device ID')
    parser.add_argument('--create-configs', action='store_true', help='Create example configuration files')
    parser.add_argument('--info', action='store_true', help='Show configuration info and exit')
    parser.add_argument('--interactive', action='store_true', help='Enter interactive mode')
    parser.add_argument('--visualize', '-v', action='store_true', help='Launch with visualization')

    args = parser.parse_args()

    # Handle device listing
    if args.list_devices:
        list_audio_devices()
        exit(0)

    # Handle device testing
    if args.test_device is not None:
        test_audio_device(args.test_device)
        exit(0)

    # Handle device finding
    if args.find_device:
        device = find_mchstreamer_device()
        if device is not None:
            print(f"Found potential MCHStreamer device: {device}")
            print(f"To use: python multispeaker_main.py --device {device}")
        exit(0)

    # Handle device selection
    device_id = args.device
    if args.select_device:
        # Determine required channels from config
        if args.config:
            temp_config = SpeakerConfig()
            temp_config.load_from_file(args.config)
            required_channels = temp_config.get_num_channels()
        else:
            required_channels = 16  # Default for 4x4 grid

        device_id = select_audio_device_interactive(required_channels)
        if device_id is None:
            print("No device selected, exiting.")
            exit(0)

    if args.create_configs:
        create_example_configs()
    elif args.info:
        spatialiser = MultiSpeakerSpatialiser(args.config, device_id)
        spatialiser.print_info()
    elif args.script:
        # Execute a tactile script
        spatialiser = MultiSpeakerSpatialiser(args.config, device_id)

        # Set the global spatialiser BEFORE any execute calls
        generate_tactile_tone.spatialiser = spatialiser

        if args.visualize:
            # Launch the visualizer and let IT handle execution - FIXED DEVICE PASSING
            import subprocess
            import sys

            try:
                visualizer_script = 'run_with_visualizer_multispeaker.py'
                cmd = [sys.executable, visualizer_script, args.script]
                if args.config:
                    cmd.extend(['--config', args.config])

                # FIXED: Pass device ID to visualizer
                if device_id is not None:
                    cmd.extend(['--device', str(device_id)])

                print("Launching visualizer to handle script execution...")
                print(f"Script: {args.script}")
                print(f"Config: {args.config if args.config else 'default'}")
                print(f"Device: {device_id if device_id is not None else 'auto'}")
                print("The visualizer will execute the script. Close the visualizer window to stop.")

                # Wait for the visualizer process to complete
                process = subprocess.Popen(cmd)
                process.wait()  # This blocks until visualizer closes
                print("Visualizer closed.")

            except Exception as e:
                print(f"Could not launch visualizer: {e}")
                print("Falling back to execution without visualization...")
                # Fallback to non-visualized execution
                try:
                    with open(args.script, 'r') as f:
                        lines = f.read().splitlines()
                    actions = parse_script(lines)
                    execute(actions)
                except Exception as fallback_error:
                    print(f"Fallback execution failed: {fallback_error}")

        else:
            # Non-visualized execution
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
                # Cleanup after execution
                try:
                    spatialiser.stop()
                except:
                    pass

    elif args.interactive:
        # Interactive mode
        spatialiser = MultiSpeakerSpatialiser(args.config, device_id)
        spatialiser.start()

        print("\nCommands:")
        print("  play x y freq amp     - Play sound at position (meters)")
        print("  load filename         - Load configuration file")
        print("  save filename         - Save configuration file")
        print("  info                  - Show speaker info")
        print("  devices               - List audio devices")
        print("  device ID             - Switch to audio device ID")
        print("  test-device ID        - Test audio device ID")
        print("  find-device           - Auto-find MCHStreamer device")
        print("  smooth                - Configure smooth tactile grid")
        print("  help                  - Show this help")
        print("  quit                  - Exit")
        print("\nExample: play 0.02 0.02 440 0.5  (20mm, 20mm)")
        print("NOTE: All channels are 0-based (first channel is 0, not 1)")
        print("IMPROVED: Smooth tactile grid spatialization (no more clicking/jumping)")
        if device_id is not None:
            print(f"Using audio device: {device_id}")

        try:
            while True:
                cmd = input("\n> ").strip().split()

                if not cmd:
                    continue

                if cmd[0] == 'quit':
                    break
                elif cmd[0] == 'play' and len(cmd) >= 3:
                    x, y = float(cmd[1]), float(cmd[2])
                    freq = float(cmd[3]) if len(cmd) > 3 else 440
                    amp = float(cmd[4]) if len(cmd) > 4 else 0.5
                    spatialiser.play_sound(x, y, freq, amp)
                elif cmd[0] == 'load' and len(cmd) > 1:
                    spatialiser.load_config(cmd[1])
                elif cmd[0] == 'save' and len(cmd) > 1:
                    spatialiser.save_config(cmd[1])
                elif cmd[0] == 'info':
                    spatialiser.print_info()
                elif cmd[0] == 'devices':
                    list_audio_devices()
                elif cmd[0] == 'device' and len(cmd) > 1:
                    try:
                        new_device_id = int(cmd[1])
                        # Stop current stream
                        spatialiser.stop()
                        # Update device ID
                        spatialiser.audio_engine.device_id = new_device_id
                        spatialiser.audio_engine._user_specified_device = True
                        # Restart with new device
                        spatialiser.start()
                        print(f"Switched to audio device {new_device_id}")
                    except ValueError:
                        print("Invalid device ID")
                    except Exception as e:
                        print(f"Error switching device: {e}")
                elif cmd[0] == 'test-device' and len(cmd) > 1:
                    try:
                        test_device_id = int(cmd[1])
                        test_audio_device(test_device_id)
                    except ValueError:
                        print("Invalid device ID")
                elif cmd[0] == 'find-device':
                    found_device = find_mchstreamer_device()
                    if found_device is not None:
                        print(f"Found potential device: {found_device}")
                        use_it = input(f"Switch to device {found_device}? (y/n): ").strip().lower()
                        if use_it == 'y':
                            try:
                                spatialiser.stop()
                                spatialiser.audio_engine.device_id = found_device
                                spatialiser.audio_engine._user_specified_device = True
                                spatialiser.start()
                                print(f"Switched to device {found_device}")
                            except Exception as e:
                                print(f"Error switching to device {found_device}: {e}")
                elif cmd[0] == 'smooth':
                    print("Tactile Grid Smoothness Options:")
                    print("1. Default (improved smoothness)")
                    print("2. Extra smooth (Gaussian mode)")
                    print("3. More focused (less smooth, more localized)")
                    print("4. Custom parameters")

                    choice = input("Select option (1-4): ").strip()

                    if choice == '1':
                        print("Using default improved smoothness")
                    elif choice == '2':
                        spatialiser.audio_engine.spat_engine.set_tactile_grid_parameters(
                            use_gaussian=True, gaussian_sigma=0.03
                        )
                        print("Activated extra smooth mode")
                    elif choice == '3':
                        spatialiser.audio_engine.spat_engine.set_tactile_grid_parameters(
                            max_active_speakers=4, distance_power=2.0, smooth_min_distance=0.005
                        )
                        print("Activated more focused mode")
                    elif choice == '4':
                        print("Available parameters:")
                        print("- use_gaussian (True/False)")
                        print("- gaussian_sigma (0.01-0.05)")
                        print("- max_active_speakers (3-8)")
                        print("- smooth_min_distance (0.001-0.02)")
                        print("- distance_power (1.0-3.0)")
                        print("- tactile_enhancement (1.0-2.0)")
                        print("Enter parameters like: use_gaussian=True gaussian_sigma=0.025")
                        params_str = input("Parameters: ").strip()

                        if params_str:
                            try:
                                params = {}
                                for param in params_str.split():
                                    key, value = param.split('=')
                                    if key in ['use_gaussian']:
                                        params[key] = value.lower() == 'true'
                                    else:
                                        params[key] = float(value)

                                spatialiser.audio_engine.spat_engine.set_tactile_grid_parameters(**params)
                            except Exception as e:
                                print(f"Error setting parameters: {e}")

                    print("Test with: play 0.02 0.0 300 0.4 (then try play -0.02 0.0 300 0.4)")

                elif cmd[0] == 'help':
                    print("Commands:")
                    print("  play x y [freq] [amp] - Play sound at position (x,y) in meters")
                    print("  load filename         - Load speaker configuration")
                    print("  save filename         - Save current configuration")
                    print("  info                  - Show detailed speaker info")
                    print("  devices               - List available audio devices")
                    print("  device ID             - Switch to audio device ID")
                    print("  test-device ID        - Test audio device ID")
                    print("  find-device           - Auto-find MCHStreamer device")
                    print("  smooth                - Configure tactile grid smoothness")
                    print("  quit                  - Exit program")
                    print("\nExamples:")
                    print("  play 0.02 0.02 440 0.5   # 20mm right, 20mm forward")
                    print("  play -0.02 -0.02 220 0.3 # 20mm left, 20mm back")
                    print("  device 60                # Switch to audio device 60")
                    print("  test-device 5            # Test audio device 5")
                    print("  find-device              # Auto-find MCHStreamer")
                    print("\nIMPORTANT: All channels are 0-based!")
                    print("IMPROVED: Smooth tactile transitions (no more clicking)")
                    print("FIXED: Strict device selection - only uses your specified device!")
                else:
                    print("Invalid command. Type 'help' for help.")

        except KeyboardInterrupt:
            pass
        finally:
            spatialiser.stop()
            print("\nGoodbye!")
    else:
        # Default: create configs if they don't exist, then demo
        if not os.path.exists('config_4x4_grid.txt'):
            print("Creating default configuration files...")
            create_example_configs()

        spatialiser = MultiSpeakerSpatialiser('config_4x4_grid.txt', device_id)
        spatialiser.start()

        print("\nDemonstrating 4x4 grid with 40mm spacing:")
        print("Playing sounds at the four corners and center...")
        print("Channels are 0-based (first channel = 0)")
        print("IMPROVED: Smooth tactile spatialization!")
        print("FIXED: Strict device selection!")
        if device_id is not None:
            print(f"Using audio device: {device_id}")

        # Demo the 4x4 grid
        positions = [
            (-0.06, -0.06, "Bottom-left"),
            (0.06, -0.06, "Bottom-right"),
            (0.06, 0.06, "Top-right"),
            (-0.06, 0.06, "Top-left"),
            (0.0, 0.0, "Center")
        ]

        for x, y, desc in positions:
            print(f"  {desc}: ({x * 1000:.0f}, {y * 1000:.0f})mm")
            spatialiser.play_sound(x, y, freq=440, amp=0.5)
            time.sleep(0.8)

        # Demo smooth movement
        print("\nDemonstrating smooth movement (left to right):")
        for i in range(10):
            x = -0.04 + (i * 0.008)  # Move from -40mm to +32mm
            spatialiser.play_sound(x, 0.0, freq=300, amp=0.4)
            time.sleep(0.2)

        spatialiser.stop()
        print("\nDemo complete. Use --interactive for interactive mode.")
        print("Use --list-devices to see available audio devices.")
        print("Use --device ID to specify an audio device.")
        print("Remember: All channels are 0-based!")
        print("IMPROVED: Smooth tactile spatialization eliminates clicking/jumping!")
        print("FIXED: Device selection now strictly enforced - no fallback!")