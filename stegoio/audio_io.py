# stegoio/audio_io.py
import wave, numpy as np

def load_wav_pcm16(path: str):
    with wave.open(path, 'rb') as w:
        nchan = w.getnchannels()
        sampw = w.getsampwidth()
        rate  = w.getframerate()
        nfrm  = w.getnframes()
        assert sampw == 2, "Only 16-bit PCM WAV supported"
        raw = w.readframes(nfrm)
    a = np.frombuffer(raw, dtype=np.int16)
    if nchan > 1:
        a = a.reshape(-1, nchan)
    return a.copy(), rate

def save_wav_pcm16(path: str, a: np.ndarray, sr: int):
    x = np.asarray(a, dtype=np.int16)
    nchan = 1 if x.ndim == 1 else x.shape[1]
    with wave.open(path, 'wb') as w:
        w.setnchannels(nchan)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(x.tobytes())
