from src.analysis.analysis import analyse_folder
from src.analysis.plotting import plot_FFT, fit_peak_frequency, plot_time_series
from src.analysis.wav_io import read_wav
from src.analysis.features import find_candidate_peaks, merge_peaks
from src.analysis.fft import FFT, extract_time_window
import argparse
import os



# frequency shift

def run(folder, actual_frequency):
    result = analyse_folder(folder, actual_frequency)
    mean_frequency = result['frequency_mean']
    std_frequency = result["frequency_std"]

    delta_f = mean_frequency - actual_frequency

    print(f"Commanded Frequency : {actual_frequency:.2f} Hz")
    print(f"Measured Frequency  : {mean_frequency:.2f} Hz")
    print(f"Frequency Std       : {std_frequency:.2f} Hz")
    print(f"Δf                  : {delta_f:.2f} Hz")
    return result


def plot_recording(data, fs, t0):
    plot_time_series(data, fs, t0, filename=None)
    plot_FFT(data, fs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--actual_frequency", type=float, required=True)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--tstart", type=float, default=1.0)
    parser.add_argument("--tend", type=float, default=3.0)

    args = parser.parse_args()
    run(args.folder, args.actual_frequency)
    if args.plot:
        wav_files = [f for f in os.listdir(args.folder) if f.endswith(".wav")]
        for i in range(len(wav_files)):
            ### print out peaks###
            filepath = os.path.join(args.folder, wav_files[i])
            data, meta = read_wav(filepath)
            segment = extract_time_window(data, meta["sample_rate"], args.tstart, args.tend)
            xf, yf = FFT(segment, meta["sample_rate"])
            peaks_freq, peaks_mag = find_candidate_peaks(segment, meta["sample_rate"])
            merged_peaks = merge_peaks(peaks_freq)

            print(f"\nFile: {wav_files[i]}")
            print("Candidate peaks:")
            for peak_freq in merged_peaks:
                f_fit, f_err = fit_peak_frequency(xf, yf, peak_freq)
                print(f"Peak near {peak_freq:.2f} Hz " f"-> {f_fit:.2f} ± {f_err:.2f} Hz")

            ###
            plot_recording(segment, meta["sample_rate"], args.tstart)

