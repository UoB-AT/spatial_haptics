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
    match = re.search(r"amp(\d+)", folder_name)
    if match:
        return float(match.group(1))/ 10.0
    return None

def extract_frequency_from_foldername(folder_name):
    match = re.search(r"(\d+(?:\.\d+)?)Hz", folder_name)
    if match:
        return float(match.group(1))
    return None

def load_data(parent_folder, tstart, tend):
    frequencies = []
    rms_values = []
    amp = None
    for subfolder in os.listdir(parent_folder):
        freq = extract_frequency_from_foldername(subfolder)
        amp = extract_amplitude_from_foldername(subfolder)
        if freq is None or amp is None:
            continue

        folder_path = os.path.join(parent_folder, subfolder)
        result = analyse_folder(folder_path, freq, tstart, tend)
        frequencies.append(freq)
        rms_values.append(result["rms_mean"])
    return frequencies, rms_values, amp


def plot_all(folders, tstart, tend):
    plt.figure(figsize=(10, 6))
    for parent_folder in folders:
        freqs, rms, amp = load_data(parent_folder, tstart, tend)
        idx = np.argsort(freqs)
        freqs = np.array(freqs)[idx]
        rms = np.array(rms)[idx]
        gain = rms / amp
        plt.plot(freqs, gain, '.', label=f"AMP = {amp:.1f}")

    plt.xlabel("Commanded Frequency (Hz)")
    plt.ylabel("RMS / Commanded Amplitude")
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument("--parent_folder", help="Path to the directory containing frequency subfolders")
    parser.add_argument("--parent_folders", nargs="+", help="Path to the directory containing frequency subfolders")
    parser.add_argument("--tstart", type=float, default=2.5)
    parser.add_argument("--tend", type=float, default=4.5)

    args = parser.parse_args()
    print(args.parent_folders)
    plot_all(args.parent_folders, args.tstart, args.tend)
