"""
Parity plot for commanded and measured frequencies
"""

from src.analysis.analysis import analyse_folder
import argparse
import os
import re
import matplotlib.pyplot as plt
import numpy as np



def extract_frequency_from_foldername(folder_name):
    match = re.search(r"(\d+(?:\.\d+)?)", folder_name)
    if match:
        return float(match.group(1))
    return None

def run_analysis(parent_folder, tstart, tend):
    commanded_frequencies = []
    measured_frequencies = []
    subfolders = os.listdir(parent_folder)
    if not subfolders:
        print(f"No subfolders found in {parent_folder}")
        return
    for subfolder in subfolders:

        actual_freq = extract_frequency_from_foldername(subfolder)

        if actual_freq is None:
            print(f"Skipping folder {subfolder}")
            continue
        folder_path = os.path.join(parent_folder, subfolder)
        if not os.path.isdir(folder_path):
            continue
        try:
            result = analyse_folder(folder_path, actual_freq, tstart, tend)
            individual_freqs = result["individual_frequencies"]

            for freq in individual_freqs:
                commanded_frequencies.append(actual_freq)
                measured_frequencies.append(freq)

        except Exception as e:
            print(f"Error processing folder {subfolder}: {e}")
    idx = np.argsort(commanded_frequencies)
    commanded_frequencies = np.array(commanded_frequencies)[idx]
    measured_frequencies = np.array(measured_frequencies)[idx]
    return commanded_frequencies, measured_frequencies


def plot_all(folders, tstart, tend):
    plt.figure(figsize=(6,6))
    plt.plot([50,250], [50,250], 'k--', linewidth=0.5)

    for i, folder in enumerate(folders):
        command, measured = run_analysis(folder, tstart, tend)
        plt.scatter(command, measured, marker='.', color='g')
    plt.xlabel("Commanded Frequency (Hz)")
    plt.ylabel("Measured Frequency (Hz)")
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent_folder", help="Path to the directory containing frequency subfolders")
    parser.add_argument("--plot_individual", action="store_true",
                        help="Analyze and print peak data for individual WAV files")
    parser.add_argument("--tstart", type=float, default=2.0)
    parser.add_argument("--tend", type=float, default=4.0)
    parser.add_argument("--parent_folders", nargs="+", help="Path to the folder containing WAV files")

    args = parser.parse_args()
    plot_all(args.parent_folders, args.tstart, args.tend)
