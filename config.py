import re
import numpy as np
import os
import time

class SpeakerConfig:
    def __init__(self):
        # Default 4x4 grid with 40mm spacing
        self.spacing = 0.04  # 40mm in meters
        self.grid_size = 4
        self.method = 'tactile_grid'
        self.speakers = []
        self.config_name = 'default_4x4'

        # Initialize default configuration
        self.create_default_grid()

    def create_default_grid(self):
        """Create default 4x4 grid with 40mm spacing - CHANNELS START AT 0."""
        self.speakers = []

        # Calculate positions for 4x4 grid centered at (0,0)
        # Grid spans from -60mm to +60mm (3 * 40mm spacing)
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                # Center the grid at (0,0)
                x = (j - (self.grid_size - 1) / 2) * self.spacing  # j for x-axis
                y = ((self.grid_size - 1 - i) - (self.grid_size - 1) / 2) * self.spacing  # Flip i for y-axis

                # Channel assignment: bottom-left = 0, increment left-to-right, bottom-to-top
                channel = i * self.grid_size + j

                speaker = {
                    'id': f'SP_{i:02d}_{j:02d}',
                    'pos': [x, y],
                    'channel': channel,  # Starts at 0
                    'row': i,
                    'col': j
                }
                self.speakers.append(speaker)

        print(f"Created default {self.grid_size}x{self.grid_size} grid with channels 0-{len(self.speakers) - 1}")

    def parse_config_line(self, line):
        """Parse a single configuration line."""
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('#'):
            return True

        # Grid command - handle this BEFORE config assignments
        if line.upper().startswith('GRID'):
            return self.parse_grid_line(line)

        # Circle array command
        if line.upper().startswith('CIRCLE'):
            return self.parse_circle_line(line)

        # Line array command
        if line.upper().startswith('LINE'):
            return self.parse_line_array(line)

        # Speaker definition
        if line.upper().startswith('SPEAKER'):
            return self.parse_speaker_line(line)

        # Configuration assignments
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip().lower()
            value = value.strip()

            if key == 'spacing':
                self.spacing = float(value)
            elif key == 'grid_size':
                self.grid_size = int(value)
                self.create_default_grid()  # Recreate with new size
            elif key == 'method':
                self.method = value.lower()
            elif key == 'config_name':
                self.config_name = value
            else:
                print(f"Warning: Unknown config parameter: {key}")
            return True

        print(f"Warning: Unknown command: {line}")
        return False

    def parse_speaker_line(self, line):
        """Parse SPEAKER command: SPEAKER ID x,y CHANNEL=n [DESCRIPTION="text"]"""
        try:
            parts = line.split()
            if len(parts) < 3:
                print(f"Warning: Invalid SPEAKER command: {line}")
                return False

            speaker_id = parts[1]
            coords = parts[2].split(',')

            if len(coords) != 2:
                print(f"Warning: Invalid coordinates in SPEAKER: {line}")
                return False

            x, y = float(coords[0]), float(coords[1])

            # Extract channel - ENFORCE 0-BASED INDEXING
            channel_match = re.search(r'CHANNEL=(\d+)', line)
            if not channel_match:
                print(f"Warning: Missing CHANNEL in SPEAKER: {line}")
                return False

            channel = int(channel_match.group(1))

            # Validate channel number
            if channel < 0:
                print(f"Warning: Channel numbers must be >= 0, got {channel}")
                return False

            # Extract optional description
            desc_match = re.search(r'DESCRIPTION="([^"]*)"', line)
            description = desc_match.group(1) if desc_match else ""

            speaker = {
                'id': speaker_id,
                'pos': [x, y],
                'channel': channel,  # 0-based channel
                'description': description
            }

            self.speakers.append(speaker)
            print(f"Added speaker {speaker_id} at channel {channel} (0-based)")
            return True

        except (ValueError, IndexError) as e:
            print(f"Warning: Error parsing SPEAKER command: {line} - {e}")
            return False

    def parse_grid_line(self, line):
        """Parse GRID command: GRID SIZE=4 SPACING=0.04 [OFFSET=0.0,0.0] - CHANNELS START AT 0"""
        try:
            # Extract parameters
            size_match = re.search(r'SIZE=(\d+)', line)
            spacing_match = re.search(r'SPACING=([0-9.]+)', line)
            offset_match = re.search(r'OFFSET=([0-9.-]+),([0-9.-]+)', line)

            if not size_match or not spacing_match:
                print(f"Warning: GRID requires SIZE and SPACING: {line}")
                return False

            size = int(size_match.group(1))
            spacing = float(spacing_match.group(1))

            offset_x, offset_y = 0.0, 0.0
            if offset_match:
                offset_x = float(offset_match.group(1))
                offset_y = float(offset_match.group(2))

            # Clear existing speakers and create grid
            self.speakers = []
            self.grid_size = size
            self.spacing = spacing

            for i in range(size):
                for j in range(size):
                    # Center the grid at offset - FIXED COORDINATE MAPPING
                    x = (j - (size - 1) / 2) * spacing + offset_x  # j maps to x
                    y = ((size - 1 - i) - (size - 1) / 2) * spacing + offset_y  # Flip i for y

                    # Channel assignment: 0-based, left-to-right, bottom-to-top
                    channel = i * size + j

                    speaker = {
                        'id': f'G_{i:02d}_{j:02d}',
                        'pos': [x, y],
                        'channel': channel,  # 0-based channels
                        'row': i,
                        'col': j
                    }
                    self.speakers.append(speaker)

            print(
                f"Created {size}x{size} grid with {spacing * 1000:.1f}mm spacing, channels 0-{len(self.speakers) - 1}")
            return True

        except (ValueError, IndexError) as e:
            print(f"Warning: Error parsing GRID command: {line} - {e}")
            return False

    def parse_circle_line(self, line):
        """Parse CIRCLE command: CIRCLE COUNT=8 RADIUS=2.0 [OFFSET=0.0,0.0] - CHANNELS START AT 0"""
        try:
            count_match = re.search(r'COUNT=(\d+)', line)
            radius_match = re.search(r'RADIUS=([0-9.]+)', line)
            offset_match = re.search(r'OFFSET=([0-9.-]+),([0-9.-]+)', line)

            if not count_match or not radius_match:
                print(f"Warning: CIRCLE requires COUNT and RADIUS: {line}")
                return False

            count = int(count_match.group(1))
            radius = float(radius_match.group(1))

            offset_x, offset_y = 0.0, 0.0
            if offset_match:
                offset_x = float(offset_match.group(1))
                offset_y = float(offset_match.group(2))

            # Clear existing speakers and create circle
            self.speakers = []

            for i in range(count):
                angle = 2 * np.pi * i / count
                x = radius * np.cos(angle) + offset_x
                y = radius * np.sin(angle) + offset_y

                speaker = {
                    'id': f'C_{i:02d}',
                    'pos': [x, y],
                    'channel': i,  # 0-based channels
                    'angle': angle * 180 / np.pi  # Store angle in degrees
                }
                self.speakers.append(speaker)

            print(f"Created {count}-speaker circle with {radius}m radius, channels 0-{count - 1}")
            return True

        except (ValueError, IndexError) as e:
            print(f"Warning: Error parsing CIRCLE command: {line} - {e}")
            return False

    def parse_line_array(self, line):
        """Parse LINE command: LINE COUNT=7 LENGTH=3.0 ANGLE=0 [OFFSET=0.0,0.0] - CHANNELS START AT 0"""
        try:
            count_match = re.search(r'COUNT=(\d+)', line)
            length_match = re.search(r'LENGTH=([0-9.]+)', line)
            angle_match = re.search(r'ANGLE=([0-9.-]+)', line)
            offset_match = re.search(r'OFFSET=([0-9.-]+),([0-9.-]+)', line)

            if not count_match or not length_match:
                print(f"Warning: LINE requires COUNT and LENGTH: {line}")
                return False

            count = int(count_match.group(1))
            length = float(length_match.group(1))
            angle = float(angle_match.group(1)) if angle_match else 0.0

            offset_x, offset_y = 0.0, 0.0
            if offset_match:
                offset_x = float(offset_match.group(1))
                offset_y = float(offset_match.group(2))

            # Clear existing speakers and create line
            self.speakers = []

            # Convert angle to radians
            angle_rad = np.radians(angle)

            for i in range(count):
                # Position along line from -length/2 to +length/2
                t = (i - (count - 1) / 2) * length / (count - 1) if count > 1 else 0

                x = t * np.cos(angle_rad) + offset_x
                y = t * np.sin(angle_rad) + offset_y

                speaker = {
                    'id': f'L_{i:02d}',
                    'pos': [x, y],
                    'channel': i,  # 0-based channels
                    'position': t  # Store position along line
                }
                self.speakers.append(speaker)

            print(f"Created {count}-speaker line array, {length}m length, channels 0-{count - 1}")
            return True

        except (ValueError, IndexError) as e:
            print(f"Warning: Error parsing LINE command: {line} - {e}")
            return False

    def load_from_file(self, filename):
        """Load speaker configuration from text file."""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()

            # Reset to defaults
            self.speakers = []
            self.method = 'tactile_grid'
            self.config_name = os.path.splitext(os.path.basename(filename))[0]

            success = True
            for line_num, line in enumerate(lines, 1):
                if not self.parse_config_line(line):
                    print(f"Error on line {line_num}: {line.strip()}")
                    success = False

            if not self.speakers:
                print("Warning: No speakers defined, using default 4x4 grid")
                self.create_default_grid()

            # Validate channel assignments
            self.validate_channels()

            return success

        except Exception as e:
            print(f"Error loading config file: {e}")
            return False

    def validate_channels(self):
        """Validate that channel assignments are correct and 0-based."""
        if not self.speakers:
            return

        channels = [sp['channel'] for sp in self.speakers]

        # Check for duplicates
        if len(channels) != len(set(channels)):
            print("WARNING: Duplicate channel assignments detected!")
            channel_counts = {}
            for ch in channels:
                channel_counts[ch] = channel_counts.get(ch, 0) + 1
            for ch, count in channel_counts.items():
                if count > 1:
                    print(f"  Channel {ch} assigned to {count} speakers")

        # Check for gaps
        min_ch, max_ch = min(channels), max(channels)
        if min_ch < 0:
            print(f"WARNING: Negative channel number found: {min_ch}")

        expected_channels = set(range(max_ch + 1))
        actual_channels = set(channels)
        missing = expected_channels - actual_channels
        if missing:
            print(f"WARNING: Missing channel assignments: {sorted(missing)}")

        print(f"Channel validation: {len(channels)} speakers using channels {min_ch}-{max_ch}")

    def save_to_file(self, filename):
        """Save current configuration to text file."""
        try:
            with open(filename, 'w') as f:
                f.write(f"# Speaker Configuration: {self.config_name}\n")
                f.write(f"# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# CHANNELS START AT 0\n\n")

                f.write(f"config_name = {self.config_name}\n")
                f.write(f"method = {self.method}\n\n")

                f.write("# Speakers (channels are 0-based)\n")
                for speaker in self.speakers:
                    x, y = speaker['pos']
                    desc = speaker.get('description', '')
                    desc_str = f' DESCRIPTION="{desc}"' if desc else ''
                    f.write(f"SPEAKER {speaker['id']} {x:.4f},{y:.4f} CHANNEL={speaker['channel']}{desc_str}\n")

            return True

        except Exception as e:
            print(f"Error saving config file: {e}")
            return False

    def get_num_channels(self):
        """Get the number of audio channels needed (0-based indexing)."""
        if not self.speakers:
            return 0
        return max(sp['channel'] for sp in self.speakers) + 1

    def get_speaker_positions(self):
        """Get array of speaker positions."""
        return np.array([sp['pos'] for sp in self.speakers])

    def print_info(self):
        """Print configuration information with clear channel mapping."""
        print(f"\n=== Speaker Configuration ===")
        print(f"Name: {self.config_name}")
        print(f"Method: {self.method}")
        print(f"Speakers: {len(self.speakers)}")
        print(f"Channels: {self.get_num_channels()} (0-based: 0 to {self.get_num_channels() - 1})")
        if self.speakers:
            positions = self.get_speaker_positions()
            x_range = np.ptp(positions[:, 0]) * 1000  # Convert to mm
            y_range = np.ptp(positions[:, 1]) * 1000
            print(f"Coverage: {x_range:.1f}mm x {y_range:.1f}mm")

        print("\nSpeaker Layout (channels are 0-based):")
        for sp in self.speakers:
            x, y = sp['pos']
            desc = sp.get('description', '')
            desc_str = f' ({desc})' if desc else ''
            print(f"  {sp['id']}: ({x * 1000:6.1f}, {y * 1000:6.1f})mm -> CH{sp['channel']}{desc_str}")

    def get_channel_map(self):
        """Get a mapping of channel numbers to speaker info for debugging."""
        channel_map = {}
        for sp in self.speakers:
            channel_map[sp['channel']] = {
                'id': sp['id'],
                'pos': sp['pos'],
                'description': sp.get('description', '')
            }
        return channel_map

