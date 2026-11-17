"""Reconstruct selected validation raw windows from verified public CWRU sources.

No training, MQTT operation or 3 HP download. Default output preserves original data.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse
import shutil

import numpy as np
from scipy.io import loadmat
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/cwru_validation')
    parser.add_argument('--offline', action='store_true', help='Require already-cached source MAT files')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/validation_2hp_windows.rebuilt.npz')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'data/source_preparation_manifest_PC_ONLY.json').read_text(encoding='utf-8'))
    sources = manifest['sources']
    assert len(sources) == 14 and {r['hp'] for r in sources} == {2}
    with (ROOT / 'data/ground_truth_PC_ONLY.csv').open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 826
    args.cache.mkdir(parents=True, exist_ok=True)
    prepared = {}
    for source in sources:
        rid = source['id']
        path = args.cache / f'{rid}.mat'
        if not path.exists():
            if args.offline:
                raise FileNotFoundError(f'Missing verified offline source: {path}')
            url = urlparse(source['url'])
            assert url.scheme == 'https' and url.hostname == 'engineering.case.edu'
            print('Downloading selected HP2 source', rid, flush=True)
            part = path.with_suffix('.mat.part')
            with urlopen(source['url'], timeout=45) as response, part.open('wb') as target:
                shutil.copyfileobj(response, target)
            assert sha256(part) == source['sha256'], f'Source hash mismatch for {rid}'
            part.replace(path)
        assert sha256(path) == source['sha256'], f'Source hash mismatch for {rid}'
        data = loadmat(path)
        assert source['de_key'] in data
        x = np.asarray(data[source['de_key']], dtype=np.float64).reshape(-1)
        assert len(x) == source['samples'] and np.isfinite(x).all()
        if source['source_fs'] == 48000:
            x = resample_poly(x, 1, 4, window=('kaiser', 5.0), padtype='constant')
        else:
            assert source['source_fs'] == 12000
        prepared[rid] = x[128:-128].astype(np.float32)
        assert (len(prepared[rid]) - 2048) // 2048 + 1 == 59
    windows = []
    for row in rows:
        assert int(row['load_hp']) == 2
        start = int(row['start_sample_12k']) - 128
        assert start >= 0 and start % 2048 == 0
        w = prepared[int(row['recording_id'])][start:start + 2048]
        assert w.shape == (2048,)
        windows.append(w)
    samples = np.stack(windows).astype('<f4')
    ids = np.asarray([r['window_id'] for r in rows], dtype='<U32')
    with np.load(ROOT / 'data/validation_2hp_windows.npz', allow_pickle=False) as original:
        assert np.array_equal(ids, original['window_ids'])
        difference = float(np.max(np.abs(samples - original['samples'])))
        assert np.allclose(samples, original['samples'], rtol=1e-7, atol=1e-7), difference
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, samples=samples, window_ids=ids)
    print('Rebuilt:', args.output)
    print('Source hashes verified: 14; windows: 826; maximum raw difference:', difference)
    print('Source rates remain reference-documented; data-level confirmation is pending.')


if __name__ == '__main__':
    main()
