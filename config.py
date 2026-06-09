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

