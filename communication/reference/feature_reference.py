import numpy as np

FEATURE_NAMES = ['rms', 'std', 'peak_to_peak', 'crest_factor', 'skewness', 'pearson_kurtosis', 'power_0_500', 'power_500_1000', 'power_1000_2000', 'power_2000_3000', 'power_3000_4000', 'power_4000_6000']

def extract_features(window):
    x = np.asarray(window, dtype=np.float64)
    if x.shape != (2048,) or not np.isfinite(x).all():
        raise ValueError('Expected 2048 finite raw samples at 12 kHz')
    c = x - x.mean()
    rms = np.sqrt(np.mean(x * x))
    std = np.sqrt(np.mean(c * c))
    if std < 1e-12:
        raise ValueError('Flat window: inspect the source data')
    time_features = [rms, std, np.ptp(x), np.max(np.abs(x)) / max(rms, 1e-12), np.mean(c ** 3) / max(std ** 3, 1e-12), np.mean(c ** 4) / max(std ** 4, 1e-12)]
    power = np.abs(np.fft.rfft(c * np.hanning(2048))) ** 2
    power[1:-1] *= 2
    power[0] = 0
    bands, _ = np.histogram(np.fft.rfftfreq(2048, d=1 / 12000), bins=[0, 500, 1000, 2000, 3000, 4000, 6000], weights=power)
    result = np.asarray(time_features + (bands / max(power.sum(), 1e-12)).tolist(), dtype=np.float32)
    if not np.isfinite(result).all():
        raise ValueError('Non-finite features')
    return result
