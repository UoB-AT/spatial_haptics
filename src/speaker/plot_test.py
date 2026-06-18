import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

def plot_channels(data, fs=48000):
    n_samples, n_channels = data.shape
    fig, axes = plt.subplots(16, 1, figsize=(12, 8), sharex=True, sharey=True)
    t = np.arange(n_samples) / fs

    for i, ax in enumerate(axes):
        ax.plot(t, data[:, i])
        ax.set_ylabel(f'ch{i+1}', rotation=0, labelpad=15)
        ax.tick_params(right=False, labelright=False)
    axes[-1].set_xlabel("Time (s)")
    plt.tight_layout()
    plt.show()

def plot_one_channel(data, channel, fs):
    t = np.arange(data.shape[0]) / fs
    plt.figure(figsize=(12, 4))
    plt.plot(t, data[:, channel-1], lw=0.8)
    plt.xlabel("Time (s)")
    plt.ylabel("Amp")
    plt.title(f"Ch {channel}")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_spectrum(data, fs):
    n_samples, n_channels = data.shape
    freqs = np.fft.rfftfreq(n_samples, d=1/fs)
    fig, axes = plt.subplots(
        n_channels, 1,
        figsize=(12, 8),
        sharex=True
    )
    if n_channels == 1:
        axes = [axes]
    for i, ax in enumerate(axes):
        x = data[:, i]
        x = x - np.mean(x)
        X = np.fft.rfft(x)
        mag = np.abs(X) / n_samples
        ax.plot(freqs, mag, lw=0.8)
        ax.set_ylabel(f'ch{i+1}', rotation=0, labelpad=15)
        ax.tick_params(right=False, labelright=False)
    axes[-1].set_xlabel('Freq (Hz)')
    plt.tight_layout()
    plt.show()

def plot_one_spectrum(data, channel, fs, fmax=None):
    x = data[:, channel-1]
    x = x - np.mean(x)  # Remove DC offset
    N = len(x)
    xf = np.fft.rfftfreq(N, d=1/fs)
    yf = np.abs(np.fft.rfft(x))
    find_peak(xf, yf)
    plt.figure(figsize=(12, 4))
    plt.plot(xf, yf)
    if fmax is not None:
        plt.xlim(0, fmax)
    plt.xlim(0, 200)
    plt.xlabel("Freq (Hz)")
    plt.ylabel("Magnitude")
    plt.title(f"Ch{channel}")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

def find_peak(xf, yf):
    peaks, _ = find_peaks(yf, height=np.max(yf) * 0.05)
    for p in peaks:
        print(f"{xf[p]:.2f} Hz, magnitude={yf[p]:.2f}")


data = np.loadtxt('output/audio_output_weighted_1781178379.txt', delimiter= ',')
# parameters
sample_rate = 48000
t_start= 2
t_end = 3

start_idx = int(t_start * sample_rate)
end_idx = int(t_end * sample_rate)
data=data[start_idx:end_idx]
#plot_channels(data, fs=48000)
#plot_spectrum(data, fs=48000)
plot_one_channel(data, channel=12, fs=sample_rate)
plot_one_spectrum(data, channel=12, fs=sample_rate)
