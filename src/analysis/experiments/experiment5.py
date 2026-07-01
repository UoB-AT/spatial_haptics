"""
Envelop Analysis (Hilbert Transform) - Try out
"""

from src.analysis.analysis import analyse_HT
import matplotlib.pyplot as plt
from src.analysis.fft import extract_time_window
from src.analysis.wav_io import read_wav
import argparse
import numpy as np
from scipy.signal import find_peaks


def find_peak_envelop(envelope, fs, command_frequency, plot=False):
    dis = int(fs / command_frequency)
    peaks, _ = find_peaks(envelope, distance=dis)
    time = np.arange(len(envelope)) / fs
    if plot:
        plt.figure(figsize=(8, 3))
        plt.plot(time, envelope, label="Envelope")
        plt.plot(time[peaks], envelope[peaks] , "ro", label="Peaks")
        plt.legend()
        plt.show()
    return peaks, envelope[peaks]


def exp_envelop_plot(peaks, peak_values, fs, duration):
    peak_times = peaks / fs
    ### search for overshoot
    search_time = 1.0  # seconds
    search_idx = np.where(peaks / fs <= search_time)[0]
    start_idx = search_idx[np.argmax(envelope_peaks[search_idx])]
    ###
    start_time = peak_times[start_idx]
    mask = ((peak_times >= start_time) & (peak_times <= start_time + duration))

    selected_times = peak_times[mask] - start_time
    selected_peaks = peak_values[mask]
    selected_peaks = selected_peaks / selected_peaks[0]
    ln_peaks = np.log(selected_peaks)
    #ln_peaks = selected_peaks
    plt.figure(figsize=(6,4))
    plt.plot(selected_times, ln_peaks, '.')
    plt.xlabel("Time after overshoot (s)")
    plt.ylabel("ln(A/A0)")
    plt.tight_layout()
    plt.show()


### try another method
def find_unsteady_duration(peaks, envelope_peaks, fs):
    window = 20
    # Mean amplitude over each window
    moving_mean = np.convolve(envelope_peaks, np.ones(window) / window, mode="valid")
    delta = np.abs(np.diff(moving_mean))
    # get the data in the middle (so it will be in steady state)
    mid = len(delta) // 2
    steady_delta = delta[mid-10: mid+10]

    threshold = np.mean(steady_delta) + 2 * np.std(steady_delta)
    ### search for overshoot
    search_time = 1.0  # seconds
    search_idx = np.where(peaks / fs <= search_time)[0]
    overshoot_idx = search_idx[np.argmax(envelope_peaks[search_idx])]
    ###
    print("mean =", np.mean(steady_delta))
    print("std  =", np.std(steady_delta))
    print("threshold =", threshold)
    N = 20 # number of consecutive windows
    steady_start = None
    for i in range(overshoot_idx, len(delta) - N):
        if np.all(delta[i:i + N] < threshold):
            steady_start = i + window // 2
            break
    print("Steady starts at peak:", steady_start)
    time = peaks / fs
    time_mean = time[window - 1:]
    plt.figure(figsize=(10, 4))
    time_delta = time_mean[1:]
    plt.plot(time_delta, delta)
    plt.axhline(threshold, color='r', linestyle='--')
    plt.xlabel("Time (s)")
    plt.ylabel("Change in moving mean")
    plt.show()
    return (peaks[steady_start] - peaks[overshoot_idx]) / fs

def plot_HT(envelope, frequency):
    time = np.arange(len(envelope)) / fs
    plt.figure(figsize=(8, 4))
    plt.plot(time, envelope)
    plt.ylabel("Envelope")
    plt.tight_layout()

    time_freq = time[:-1]
    plt.figure(figsize=(8, 4))
    plt.plot(time_freq, frequency)
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency (Hz)")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--tstart", type=float, default=0.0)
    parser.add_argument("--tend", type=float, default=6.0)
    parser.add_argument("--duration", type=float, default=0.05)
    parser.add_argument("--commanded_freq", type=float, required=True, help="Commanded vibration frequency (Hz)")

    args = parser.parse_args()

    result = analyse_HT(args.folder, args.tstart, args.tend)
    envelope = result["envelope"]
    phase = result["phase"]
    frequency= result["instantaneous_frequency"]
    fs = result["fs"]


    if args.plot:
        plot_HT(envelope, frequency)

    peaks, envelope_peaks = find_peak_envelop(envelope, fs, args.commanded_freq) #change to commanded frequency
    exp_envelop_plot(peaks, envelope_peaks, fs, args.duration)
    settle_time = find_unsteady_duration(peaks, envelope_peaks, fs)
    print("settle_time:", settle_time)


