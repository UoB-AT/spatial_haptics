import numpy as np 
from scipy.signal import find_peaks
from .fft import FFT

def RMS_energy(data):
    return np.sqrt(np.mean(np.abs(data) ** 2))

def find_candidate_peaks(data, fs):
    xf, yf = FFT(data, fs)
    peaks, _ = find_peaks(yf, prominence=np.max(yf) * 0.3)
    return xf[peaks], yf[peaks]


def merge_peaks(peaks, tolerance=5.0):
    if len(peaks) == 0:
        return np.array([])
    # no need to sort the array
    merged = []
    current = [peaks[0]]
    for peak in peaks[1:]:
        if peak - current[-1] <= tolerance:
            current.append(peak)
        else:
            merged.append(np.mean(current))
            current = [peak]
    merged.append(np.mean(current))
    return np.array(merged)