from .wav_io import read_wav, list_files
from .fft import dominant_frequency
from .features import RMS_energy
import numpy as np
import os
import argparse

def analyse(filepath, f_command):
    data, meta = read_wav(filepath)
    fs = meta["sample_rate"]
    f_peak = dominant_frequency(data, fs, f_command)
    rms = RMS_energy(data)
    return {"f_peak": f_peak, "rms": rms}

def analyse_folder(folder, f_command):
    files = list_files(folder)
    frequencies = []
    rms_values = []
    for file in files:
        result = analyse(file, f_command)
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
        "n": len(frequencies)
    }

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--filepath")
#     parser.add_argument("--fcommand", type=float, required=True)
#     args = parser.parse_args()
#     if os.path.isdir(args.filepath):
#         result = analyse_folder(args.filepath, args.fcommand)
#         print(f"Mean Frequency: " f"{result['frequency_mean']:.2f} Hz")
#         print(f"Frequency Std: " f"{result['frequency_std']:.2f} Hz")
#         print(f"Mean RMS: " f"{result['rms_mean']:.6f}")
#         print(f"RMS Std: " f"{result['rms_std']:.6f}")
#     else:
#         result = analyse(args.filepath, args.fcommand)
#         print(f"Dominant Frequency: {result['f_peak']:.2f} Hz")
#         print(f"RMS Amplitude: {result['rms']:.6f}")
