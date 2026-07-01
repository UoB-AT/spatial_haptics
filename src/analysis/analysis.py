from .wav_io import read_wav, list_files
from .fft import dominant_frequency, extract_time_window
from .features import RMS_energy
import numpy as np
import os
from scipy.signal import hilbert
from scipy.signal import butter, filtfilt

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

def analyse_HT(filepath, tstart, tend):
    data, meta = read_wav(filepath)
    fs = meta["sample_rate"]
    ### add high pass filtering
    cutoff_freq = 20
    order = 4
    nyq = 0.5 * fs
    normal_cutoff = cutoff_freq / nyq
    b, a = butter(order, normal_cutoff, btype='highpass')
    ###
    data = extract_time_window(data, fs, tstart, tend)
    data = filtfilt(b, a, data) # filtered
    analytic_signal= hilbert(data)
    envelope = np.abs(analytic_signal)
    phase = np.unwrap(np.angle(analytic_signal))
    frequency = np.diff(phase) / (2.0 * np.pi) * fs
    return {"fs": fs,
            "envelope": envelope,
            "envelope_mean": np.mean(envelope),
            "envelope_std": np.std(envelope),
            "phase": phase,
            "instantaneous_frequency": frequency
            }


def analyse_folder_HT(folder_path, tstart, tend):
    envelope_means = []
    envelope_stds = []
    for filename in os.listdir(folder_path):
        if not filename.endswith(".wav"):
            continue
        filepath = os.path.join(folder_path, filename)
        result = analyse_HT(filepath, tstart, tend)
        envelope_means.append(result["envelope_mean"])
        envelope_stds.append(result["envelope_std"])
    return {"envelope_mean": np.mean(envelope_means),
        "envelope_std": np.std(envelope_means)
        }