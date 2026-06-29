"""
Parity plot for measured amplitude over frequencies
"""

from src.analysis.analysis import analyse_folder
import argparse
import os
import re
import matplotlib.pyplot as plt
import numpy as np



def extract_amplitude_from_foldername(folder_name):
    match = re.search(r"(\d+(?:\.\d+)?)", folder_name)
    if match:
        return float(match.group(1))
    return None


def load_data(parent_folder, tstart, tend):
    frequencies = []
    rms_values = []
    for subfolder in os.listdir(parent_folder):
        freq = extract_amplitude_from_foldername(subfolder)
        if freq is None:
            continue
        folder_path = os.path.join(parent_folder, subfolder)
        result = analyse_folder(folder_path, freq, tstart, tend)
        rms_mean = result["rms_mean"]
        frequencies.append(freq)
        rms_values.append(rms_mean)
    return frequencies, rms_values


def plot_all(folders, tstart, tend):
    plt.figure(figsize=(10, 6))
    labels = ['AMP=0.1', 'AMP=0.3', 'AMP=0.6', 'AMP=1.0']
    amp = [0.1, 0.3, 0.6, 1.0]
    for i, folder in enumerate(folders):
        freqs, rms = load_data(folder, tstart, tend)
        idx = np.argsort(freqs)
        freqs = np.array(freqs)[idx]
        rms =  np.array(rms)[idx] / amp[i]
        plt.plot(freqs, rms, '.', label=labels[i])
    plt.xlabel("Commanded Frequency (Hz)")
    plt.ylabel("RMS / Commanded Amplitude")
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent_folder", help="Path to the directory containing frequency subfolders")
    parser.add_argument("--plot_individual", action="store_true",
                        help="Analyze and print peak data for individual WAV files")
    parser.add_argument("--parent_folders", nargs="+")
    parser.add_argument("--tstart", type=float, default=2.0)
    parser.add_argument("--tend", type=float, default=4.0)

    args = parser.parse_args()
    plot_all(args.parent_folders, args.tstart, args.tend)
