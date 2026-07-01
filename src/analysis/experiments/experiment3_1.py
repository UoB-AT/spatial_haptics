"""
Parity plot for commanded and measured amplitude
"""

from src.analysis.analysis import analyse_folder
import argparse
import os
import re
import matplotlib.pyplot as plt
import numpy as np



def extract_amplitude_from_foldername(folder_name):
    match = re.search(r"amp(\d+(?:\.\d+)?)", folder_name)
    if match:
        return float(match.group(1))
    return None

def run_analysis(parent_folder, tstart, tend):
    commanded_amplitudes = []
    measured_rms = []
    std_rms = []

    subfolders = os.listdir(parent_folder)
    if not subfolders:
        print(f"No subfolders found in {parent_folder}")
        return
    for subfolder in subfolders:
        actual_amp = extract_amplitude_from_foldername(subfolder)
        if actual_amp is None:
            continue
        folder_path = os.path.join(parent_folder, subfolder)
        if not os.path.isdir(folder_path):
            continue

        try:
            result = analyse_folder(folder_path, actual_amp, tstart, tend)
            print(actual_amp)
            commanded_amplitudes.append(actual_amp/10)
            measured_rms.append(result["rms_mean"])
            std_rms.append(result["rms_std"])

        except Exception as e:
            print(f"Error processing folder {subfolder}: {e}")
    idx = np.argsort(commanded_amplitudes)
    commanded_amplitudes = np.array(commanded_amplitudes)[idx]
    measured_rms = np.array(measured_rms)[idx]
    std_rms = np.array(std_rms)[idx]
    return commanded_amplitudes, measured_rms, std_rms


def plot_all(folders, labels, tstart, tend):

    plt.figure(figsize=(5,5))

    plt.plot([0,1], [0,1], 'k--', color='black', linewidth=0.5)
    for i, folder in enumerate(folders):
        command, rms, rms_std = run_analysis(folder, tstart, tend)
        command_norm = command / np.max(command)
        rms_norm = rms / np.max(rms)
        plt.errorbar(command_norm, rms_norm, yerr=rms_std/np.max(rms), fmt='.', label=f"{labels[i]} Hz")

    plt.xlabel('Commanded Amplitude (a.u.)')
    plt.ylabel('Normalised Measured Amplitude (a.u.)')
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument("--parent_folder", help="Path to the directory containing frequency subfolders")
    # parser.add_argument("--plot_individual", action="store_true",
    #                     help="Analyze and print peak data for individual WAV files")
    parser.add_argument("--parent_folders",  nargs="+", required= True, help="Path to the directories containing frequency subfolders")
    parser.add_argument("--tstart", type=float, default=2.0)
    parser.add_argument("--tend", type=float, default=4.0)
    parser.add_argument("--labels", nargs="+", type=float, required=True, help="Labels for each dataset (e.g. frequencies)")

    args = parser.parse_args()
    plot_all(args.parent_folders, args.labels, args.tstart, args.tend)
