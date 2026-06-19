import matplotlib.pyplot as plt
import numpy as np 
from scipy import signal
from .fft import FFT
from scipy.optimize import curve_fit


def plot_time_series(data, fs, t0, filename, save=False):
    time= np.arange(len(data)) / fs +t0
    plt.figure(figsize=(12,4))
    plt.plot(time, data)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    if save:
        plt.savefig(filename, dpi=300)
        plt.close()
    else:
        plt.show()


def plot_FFT(data, fs, cutoff_freq=800):
    xf, yf = FFT(data, fs)
    mask = xf <= cutoff_freq
    plt.figure(figsize=(12,4))
    plt.plot(xf[mask], yf[mask])
    plt.show()

def plot_spectrogram(data, fs, filename=None, cutoff_freq=10000, save=False):
    f, t, Sxx = signal.spectrogram(
        data,
        fs=fs,
        nperseg=256,
        noverlap=128
    )
    mask = f <= cutoff_freq
    f = f[mask]
    Sxx = Sxx[mask]
    plt.figure(figsize=(12,4))
    plt.imshow(
        10*np.log10(Sxx + 1e-12),
        aspect='auto',
        origin='lower',
        extent=[t.min(), t.max(), f.min(), f.max()]
    )
    plt.ylabel("Freq (Hz)")
    plt.xlabel("Time (s)")
    plt.colorbar(label="Power (dB)")
    if save:
        plt.savefig(filename, dpi=300)
        plt.close()
    else:
        plt.show()

def gaussian(x, A, mu, sigma):
    return A * np.exp(-(x - mu) ** 2 / (2 * sigma ** 2))

def fit_peak_frequency(xf, yf, peak_freq, window = 5):
    mask = ((xf >= peak_freq - window) & (xf <= peak_freq + window))
    xf_fit = xf[mask]
    yf_fit = yf[mask]
    initial_guess = [np.max(yf_fit), peak_freq, 1.0]
    try:
        popt, pcov = curve_fit(gaussian, xf_fit, yf_fit, p0=initial_guess, maxfev=10000)
        f_fit = popt[1]
        f_err = np.sqrt(pcov[1,1])
        return f_fit, f_err
    except RuntimeError:
        print(f"Gaussian fit failed for {peak_freq}")
        return peak_freq, np.nan
