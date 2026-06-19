import os 
from scipy.io import wavfile
from pathlib import Path

def list_files(folder):
    return list(Path(folder).glob("*.wav"))


def read_wav(filename):
    sample_rate, data = wavfile.read(filename)
    metadata = {
        "sample_rate": sample_rate,
        "shape": data.shape,
        "dtype": str(data.dtype),
        "num_samples": len(data),
        "duration_seconds": len(data) / sample_rate,
    }
    return data, metadata

def extract_window(data, fs, t_start, t_end):
    start_idx = int(t_start * fs)
    end_idx = int(t_end * fs)
    return data[start_idx:end_idx]