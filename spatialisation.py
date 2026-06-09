import numpy as np

class SpatializationEngine:
    def __init__(self, speaker_config):
        self.config = speaker_config
        self.method = speaker_config.method

        # Parameters for different methods
        self.speed_of_sound = 343.0  # m/s
        self.itd_exaggeration = 1.0
        self.ild_exponent = 1.0
        self.distance_rolloff = 2.0
        self.tactile_exaggeration = 4.0  # Extra exaggeration for tactile

    def set_parameters(self, **kwargs):
        """Set spatialization parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def calculate_gains_delays(self, source_pos):
        """Calculate gains and delays for all speakers based on source position."""
        speakers = self.config.get_speaker_positions()
        num_speakers = len(speakers)

        gains = np.zeros(num_speakers)
        delays = np.zeros(num_speakers)

        if self.method == 'itd_ild':
            return self._calculate_itd_ild(source_pos, speakers)
        elif self.method == 'distance_pan':
            return self._calculate_distance_pan(source_pos, speakers)
        elif self.method == 'vbap':
            return self._calculate_vbap(source_pos, speakers)
        elif self.method == 'nearest_neighbor':
            return self._calculate_nearest_neighbor(source_pos, speakers)
        elif self.method == 'tactile_grid':
            return self._calculate_tactile_grid(source_pos, speakers)
        else:
            # Default: tactile grid for grid setups
            return self._calculate_tactile_grid(source_pos, speakers)

    def _calculate_nearest_neighbor(self, source_pos, speakers):
        """Nearest neighbor - only the closest speaker plays."""
        num_speakers = len(speakers)
        gains = np.zeros(num_speakers)
        delays = np.zeros(num_speakers)

        distances = np.array([np.linalg.norm(source_pos - sp) for sp in speakers])
        nearest_idx = np.argmin(distances)

        gains[nearest_idx] = 1.0

        return gains, delays

    def _calculate_tactile_grid(self, source_pos, speakers):
        """Tactile grid with smooth interpolation between adjacent speakers - FIXED VERSION."""
        num_speakers = len(speakers)
        gains = np.zeros(num_speakers)
        delays = np.zeros(num_speakers)

        # Calculate distances to all speakers
        distances = np.array([np.linalg.norm(source_pos - sp) for sp in speakers])

        # METHOD 1: Gaussian-based weighting for very smooth transitions
        # This provides the smoothest transitions but may feel less "localized"
        if hasattr(self, 'use_gaussian') and self.use_gaussian:
            # Use Gaussian falloff for very smooth transitions
            sigma = getattr(self, 'gaussian_sigma', 0.025)  # 25mm standard deviation - adjust for more/less smoothing
            weights = np.exp(-(distances ** 2) / (2 * sigma ** 2))
            gains = weights

            # Power normalization to maintain consistent perceived loudness
            total_power = np.sum(gains ** 2)
            if total_power > 0:
                gains = gains / np.sqrt(total_power)

        else:
            # METHOD 2: Improved inverse distance with smooth minimum (DEFAULT)
            # Find the nearest speakers for focused spatialization
            max_speakers = getattr(self, 'max_active_speakers', 6)  # Configurable number of active speakers
            nearest_indices = np.argsort(distances)[:min(max_speakers, num_speakers)]

            # Use smooth inverse distance weighting with larger minimum distance
            min_dist = getattr(self, 'smooth_min_distance', 0.008)  # 8mm minimum distance for smoother transitions
            distance_power = getattr(self, 'distance_power', 1.5)  # Power for distance falloff

            # Calculate weights for nearest speakers only
            total_weight = 0
            for idx in nearest_indices:
                dist = distances[idx]
                # Smooth inverse distance - less sharp than 1/d
                weight = 1.0 / ((dist + min_dist) ** distance_power)
                gains[idx] = weight
                total_weight += weight

            # Normalize weights to sum to 1
            if total_weight > 0:
                for idx in nearest_indices:
                    gains[idx] /= total_weight

            # Apply gentle overall tactile enhancement to all active speakers
            # This maintains tactile sensation without creating bias
            active_mask = gains > 0.001
            if np.any(active_mask):
                # Gentle enhancement: boost all active speakers slightly
                enhancement = getattr(self, 'tactile_enhancement', 1.2)  # Much gentler than the previous 4.0
                gains[active_mask] *= enhancement

                # Power normalization to prevent clipping and maintain consistency
                total_power = np.sum(gains ** 2)
                if total_power > 1.0:
                    gains = gains / np.sqrt(total_power)

        return gains, delays

    def set_tactile_grid_parameters(self, **kwargs):
        """Set parameters for tactile grid spatialization to fine-tune smoothness."""
        for key, value in kwargs.items():
            if key in ['use_gaussian', 'gaussian_sigma', 'max_active_speakers',
                       'smooth_min_distance', 'distance_power', 'tactile_enhancement']:
                setattr(self, key, value)
                print(f"Set {key} = {value}")
            else:
                print(f"Warning: Unknown parameter {key}")

        print("Tactile grid parameters updated. Test with a movement pattern to feel the difference.")

    def _calculate_distance_pan(self, source_pos, speakers):
        """Simple distance-based amplitude panning."""
        num_speakers = len(speakers)
        gains = np.zeros(num_speakers)
        delays = np.zeros(num_speakers)

        distances = np.array([np.linalg.norm(source_pos - sp) for sp in speakers])

        # Avoid division by zero
        distances = np.maximum(distances, 0.001)  # 1mm minimum

        # Inverse distance law
        raw_gains = 1.0 / (distances ** self.distance_rolloff)

        # Normalize gains
        total_power = np.sum(raw_gains ** 2)
        if total_power > 0:
            gains = raw_gains / np.sqrt(total_power)

        return gains, delays

    def _calculate_vbap(self, source_pos, speakers):
        """Vector Base Amplitude Panning (simplified 2D version)."""
        num_speakers = len(speakers)
        gains = np.zeros(num_speakers)
        delays = np.zeros(num_speakers)

        # Convert to polar coordinates
        source_angle = np.arctan2(source_pos[1], source_pos[0])
        if source_angle < 0:
            source_angle += 2 * np.pi

        # Calculate speaker angles
        speaker_angles = []
        for sp in speakers:
            angle = np.arctan2(sp[1], sp[0])
            if angle < 0:
                angle += 2 * np.pi
            speaker_angles.append(angle)

        speaker_angles = np.array(speaker_angles)

        # Find the two nearest speakers
        angle_diffs = np.abs(speaker_angles - source_angle)
        # Handle wraparound
        angle_diffs = np.minimum(angle_diffs, 2 * np.pi - angle_diffs)

        # Sort by angle difference
        sorted_indices = np.argsort(angle_diffs)

        # Use the two closest speakers
        sp1_idx = sorted_indices[0]
        sp2_idx = sorted_indices[1] if len(sorted_indices) > 1 else sorted_indices[0]

        if sp1_idx != sp2_idx:
            # Calculate gains using VBAP formula (simplified)
            angle1 = speaker_angles[sp1_idx]
            angle2 = speaker_angles[sp2_idx]

            # Ensure angle2 > angle1 (handle wraparound)
            if angle2 < angle1:
                if source_angle < angle1:
                    source_angle += 2 * np.pi
                angle2 += 2 * np.pi

            # Linear interpolation between the two speakers
            if angle2 != angle1:
                t = (source_angle - angle1) / (angle2 - angle1)
                t = np.clip(t, 0, 1)

                gains[sp1_idx] = np.sqrt(1 - t)
                gains[sp2_idx] = np.sqrt(t)
            else:
                gains[sp1_idx] = 1.0
        else:
            gains[sp1_idx] = 1.0

        return gains, delays

    def _calculate_itd_ild(self, source_pos, speakers):
        """Original ITD/ILD method for tactile systems."""
        num_speakers = len(speakers)
        gains = np.zeros(num_speakers)
        delays = np.zeros(num_speakers)

        if num_speakers < 2:
            if num_speakers == 1:
                gains[0] = 1.0
            return gains, delays

        for i, speaker_pos in enumerate(speakers):
            distance = np.linalg.norm(source_pos - speaker_pos)

            # ITD calculation (only for first two speakers)
            if i < 2:
                if i == 0:  # Left speaker
                    ref_distance = np.linalg.norm(source_pos - speakers[1])
                    time_diff = (distance - ref_distance) / self.speed_of_sound
                    delays[i] = time_diff * self.itd_exaggeration
                else:  # Right speaker
                    ref_distance = np.linalg.norm(source_pos - speakers[0])
                    time_diff = (distance - ref_distance) / self.speed_of_sound
                    delays[i] = time_diff * self.itd_exaggeration

            # ILD calculation
            if num_speakers == 2:
                if i == 0:  # Left
                    right_dist = np.linalg.norm(source_pos - speakers[1])
                    gains[i] = 1.0 if distance <= right_dist else (right_dist / distance) ** self.ild_exponent
                else:  # Right
                    left_dist = np.linalg.norm(source_pos - speakers[0])
                    gains[i] = 1.0 if distance <= left_dist else (left_dist / distance) ** self.ild_exponent
            else:
                gains[i] = 1.0 / (distance + 0.001)  # Avoid division by zero

        return gains, delays
