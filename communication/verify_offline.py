"""Verify packaged data, CRC codec and current PC reference inference without network access.

No MQTT connection, model training or ESP32 execution. Ground truth remains PC-side.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'protocol'))
sys.path.insert(0, str(ROOT / 'reference'))
from packet_reference import encode_window, decode_window, PACKET_BYTES
from feature_reference import extract_features
from forward_reference import load_reference_model


def main():
    checks = []
    for line in (ROOT / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        path = (ROOT / name).resolve()
        assert path.is_relative_to(ROOT.resolve())
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f'Package hash mismatch: {name}'
        checks.append(name)
    with np.load(ROOT / 'data/validation_2hp_windows.npz', allow_pickle=False) as f:
        samples, window_ids = f['samples'], f['window_ids']
        assert set(f.files) == {'samples', 'window_ids'}
    assert samples.shape == (826, 2048) and samples.dtype.str == '<f4'
    assert len(set(window_ids.tolist())) == len(window_ids) == 826
    assert np.isfinite(samples).all()
    for wid in window_ids:
        assert uuid.UUID(str(wid)).hex == str(wid)
    with (ROOT / 'data/ground_truth_PC_ONLY.csv').open(newline='', encoding='utf-8') as f:
        truth_rows = list(csv.DictReader(f))
    truth = {r['window_id']: r for r in truth_rows}
    assert len(truth) == 826 and set(truth) == set(window_ids.tolist())
    assert {int(r['load_hp']) for r in truth_rows} == {2}
    assert len({int(r['recording_id']) for r in truth_rows}) == 14
    labels = np.asarray([int(truth[str(wid)]['class_id']) for wid in window_ids])
    assert np.bincount(labels, minlength=4).tolist() == [59, 177, 413, 177]

    # Protocol test: shuffled replay indices, fresh run ID, neutral IDs, unchanged samples.
    run_id = uuid.uuid4().hex
    order = np.random.default_rng(462).permutation(len(window_ids))
    for sequence, i in enumerate(order):
        packet = encode_window(samples[i], run_id, str(window_ids[i]), sequence)
        assert len(packet) == PACKET_BYTES == 8248
        decoded = decode_window(packet)
        assert decoded['run_id'] == run_id and decoded['window_id'] == str(window_ids[i])
        assert decoded['sequence'] == sequence and np.array_equal(decoded['samples'], samples[i])
    example = (ROOT / 'protocol/example_window_packet.bin').read_bytes()
    example_decoded = decode_window(example)
    example_index = window_ids.tolist().index(example_decoded['window_id'])
    assert np.array_equal(example_decoded['samples'], samples[example_index])
    corrupt = bytearray(example)
    corrupt[100] ^= 1
    rejected = 0
    for bad in (bytes(corrupt), example[:-1]):
        try:
            decode_window(bad)
        except ValueError:
            rejected += 1
    assert rejected == 2

    with np.load(ROOT / 'reference/normalization.npz', allow_pickle=False) as f:
        mean, scale = f['mean'], f['scale']
    with np.load(ROOT / 'reference/expected_outputs_validation_PC_ONLY.npz', allow_pickle=False) as f:
        expected = {k: f[k] for k in f.files}
    assert np.array_equal(window_ids, expected['window_ids'])
    features = np.stack([extract_features(w) for w in samples])
    normalized = ((features - mean) / scale).astype(np.float32)
    assert np.allclose(features, expected['features'], rtol=1e-5, atol=2e-6)
    assert np.allclose(normalized, expected['normalized_inputs'], rtol=1e-5, atol=2e-6)
    infer = load_reference_model((ROOT / 'reference/current_baseline_fp32.tflite').read_bytes())
    scores = infer(normalized)
    assert np.allclose(scores, expected['scores'], rtol=1e-5, atol=1e-5)
    predictions = scores.argmax(axis=1)
    assert np.array_equal(predictions, expected['predicted_classes'])
    cm = np.zeros((4, 4), dtype=int)
    np.add.at(cm, (labels, predictions), 1)
    assert int(np.trace(cm)) == 825
    report = dict(status='PASS', package_files_hashed=len(checks), windows=826,
        validation_recordings=14, raw_shape=list(samples.shape), packet_bytes=PACKET_BYTES,
        shuffled_codec_roundtrips=826, invalid_packet_checks_rejected=rejected,
        reference_inference='NumPy forward pass from FP32 exported weights; no training',
        reference_correct=int(np.trace(cm)), reference_total=len(labels),
        reference_accuracy=float(np.mean(predictions == labels)), confusion_matrix=cm.tolist(),
        feature_max_abs_difference=float(np.max(np.abs(features-expected['features']))),
        score_max_abs_difference=float(np.max(np.abs(scores-expected['scores']))),
        source_rates='reference documented; data-level confirmation pending',
        network_used=False, model_training_performed=False, mqtt_or_esp32_test=False)
    (ROOT / 'OFFLINE_VERIFICATION_RESULT.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('This verifies packaged PC data/codec/reference inference, not MQTT or ESP32 integration.')


if __name__ == '__main__':
    main()
