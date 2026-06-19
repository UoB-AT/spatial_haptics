import numpy as np 

def FFT(data, sample_rate):
    yf = np.fft.rfft(data)
    xf = np.fft.rfftfreq(len(data), d=1 / sample_rate)
    return xf, np.abs(yf)/len(data) # normalisation

def calculate_spectral_centroid(data, fs):
    xf, yf = FFT(data, fs)
    return np.sum(xf * yf) / np.sum(yf)

def calculate_energy_fraction(data, fs, lower=0, upper=2500):
    data = data[:]
    xf, yf = FFT(data, fs)
    mask = (xf >= lower) & (xf < upper)
    energy_band = np.sum(yf[mask] ** 2)
    energy_total = np.sum(yf ** 2)
    return energy_band / energy_total

def dominant_frequency(data, fs, f_command=None):
    xf, yf = FFT(data, fs)
    if f_command is not None:
        mask = ((xf >= f_command - 20) & (xf <= f_command + 20))
        peak_idx = np.argmax(yf[mask])
        return xf[mask][peak_idx]

    peak_idx = np.argmax(yf)
    return xf[peak_idx]

def extract_time_window(data, fs, start_time, end_time):
    start_idx = int(start_time * fs)
    end_idx = int(end_time * fs)
    return data[start_idx:end_idx]