import json
from pathlib import Path
import numpy as np
from ai_edge_litert.interpreter import Interpreter
from feature_reference import extract_features

folder = Path(__file__).resolve().parent
with np.load(folder / 'raw_reference_PC_ONLY.npz', allow_pickle=False) as f:
    raw, reference_features = f['raw_windows'], f['features']
    reference_inputs, reference_scores, labels = f['normalized_inputs'], f['scores'], f['labels']
with np.load(folder / 'normalization.npz', allow_pickle=False) as f:
    mean, scale = f['mean'], f['scale']
features = np.stack([extract_features(w) for w in raw])
inputs = ((features-mean)/scale).astype(np.float32)
assert np.allclose(features, reference_features, rtol=1e-5, atol=1e-5)
assert np.allclose(inputs, reference_inputs, rtol=1e-5, atol=1e-5)
interpreter = Interpreter(model_path=str(folder / 'baseline_fp32.tflite'))
interpreter.allocate_tensors()
inp, out = interpreter.get_input_details()[0], interpreter.get_output_details()[0]
scores = []
for row in inputs:
    interpreter.set_tensor(inp['index'], row[None, :])
    interpreter.invoke()
    scores.append(interpreter.get_tensor(out['index'])[0].copy())
scores = np.stack(scores)
assert np.allclose(scores, reference_scores, rtol=1e-5, atol=1e-5)
assert np.array_equal(scores.argmax(axis=1), reference_scores.argmax(axis=1))
result = dict(reference_windows=len(raw), raw_feature_and_normalization_match=True,
    predicted_classes_match=True, max_score_difference=float(np.max(np.abs(scores-reference_scores))),
    reference_validation_accuracy=float(np.mean(scores.argmax(axis=1) == labels)),
    scope='PC raw-window parity; not an ESP32 test or new-data evaluation',
    offline_status='operator must record whether network was disconnected')
(folder / 'local_reference_check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('FULL RAW REFERENCE CHECK PASSED')
print(json.dumps(result, indent=2))
