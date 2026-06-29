from .wav_io import read_wav, list_files
from .fft import dominant_frequency, extract_time_window
from .features import RMS_energy
import numpy as np
import os
import argparse

def analyse(filepath, f_command, tstart, tend):
    data, meta = read_wav(filepath)
    fs = meta["sample_rate"]
    data = extract_time_window(data, fs, tstart, tend)
    f_peak = dominant_frequency(data, fs, f_command)
    rms = RMS_energy(data)
    return {"f_peak": f_peak, "rms": rms}

def analyse_folder(folder, f_command, tstart, tend):
    files = list_files(folder)
    frequencies = []
    rms_values = []
    for file in files:
        result = analyse(file, f_command, tstart, tend)
        frequencies.append(result["f_peak"])
        rms_values.append(result["rms"])

    print("\nAll frequencies:")
    print(frequencies)

    print("\nAll RMS values:")
    print(rms_values)

    return {
        "frequency_mean": np.mean(frequencies),
        "frequency_std": np.std(frequencies),
        "rms_mean": np.mean(rms_values),
        "rms_std": np.std(rms_values),
        "n": len(frequencies),
        "individual_frequencies": frequencies,
        "individual_rms": rms_values
    }

