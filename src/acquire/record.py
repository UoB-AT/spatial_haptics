import sounddevice as sd 
from scipy.io.wavfile import write 
import argparse



def record(duration, filename, samplerate):
    #input("Press Enter to start recording...")
    print("Recording...")
    audio = sd.rec(int(duration * samplerate), 
                samplerate=samplerate,
                channels=1, 
                dtype='float32')
    sd.wait()
    write(filename, samplerate, audio)
    print("Data saved to {}...".format(filename))  





