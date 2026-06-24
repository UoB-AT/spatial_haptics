"""
Parity plot for commanded and measured frequencies
"""

from src.analysis.analysis import analyse_folder
import argparse
import os
import re
import matplotlib.pyplot as plt



def extract_frequency_from_foldername(folder_name):
    match = re.search(r"(\d+(?:\.\d+)?)", folder_name)
    if match:
        return float(match.group(1))
    return None

def run_analysis_and_plot(parent_folder, tstart, tend):
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
            result = analyse_folder(folder_path, actual_freq)
            individual_freqs = result["individual_frequencies"]

            for freq in individual_freqs:
                commanded_frequencies.append(actual_freq)
                measured_frequencies.append(freq)

        except Exception as e:
            print(f"Error processing folder {subfolder}: {e}")

    if commanded_frequencies:
        plot(commanded_frequencies, measured_frequencies)


def plot(command_frequencies, measured_frequencies):

    plt.figure(figsize=(5,5))

    min_f = min(min(command_frequencies), min(measured_frequencies))
    max_f = max(max(command_frequencies), max(measured_frequencies))

    plt.plot([min_f, max_f], [min_f, max_f], 'k--', color='black', linewidth=0.5)

    plt.scatter(command_frequencies, measured_frequencies, marker='x')

    plt.xlabel('Commanded Frequency (Hz)')
    plt.ylabel('Measured Frequency (Hz)')

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent_folder", required=True, help="Path to the directory containing frequency subfolders")
    parser.add_argument("--plot_individual", action="store_true",
                        help="Analyze and print peak data for individual WAV files")
    parser.add_argument("--tstart", type=float, default=2.0)
    parser.add_argument("--tend", type=float, default=4.0)

    args = parser.parse_args()
    run_analysis_and_plot(args.parent_folder, args.tstart, args.tend)
