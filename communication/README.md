# Communication data and interface handoff

This folder contains the **complete currently selected 826-window 2 HP development
validation replay**, plus a small 14-window smoke subset. It is a data/reference handoff,
not a completed MQTT sender, dashboard, ESP32 firmware, or final-test submission.

## Start here

1. Install the PC verification dependency once: `python -m pip install -r requirements.txt`.
2. With internet disconnected if desired, run `python verify_offline.py`.
3. Read `protocol/COMMUNICATION_CONTRACT.md` and agree the proposed packet and error policies
   with the ESP32 owner before implementing either end.
4. Load `data/validation_2hp_windows.npz` with `allow_pickle=False`. It contains only
   `samples` (826,2048), float32 little-endian, and `window_ids` (826,), opaque UUID strings.
5. Shuffle indices at each replay run, assign sequence numbers **after** shuffling, and
   encode each raw row with `protocol/packet_reference.py`. Pass raw values unchanged.
6. Join actual ESP32 results to `data/ground_truth_PC_ONLY.csv` on the PC. Keep labels and
   source metadata out of input payloads, topics and identifiers.

The raw samples are already prepared at 12 kHz. Do not standardize them, re-extract features
on the sender, or resample them again. ESP32 receives raw samples and computes the features,
normalization and inference. The `.tflite` itself accepts 12 normalized features.

## Existing firmware compatibility

The current `firmware/mqtt_bridge` implements the earlier `Hello ESP32` / `Hello PC`
connectivity test only. It does not yet implement this raw-window or inference-result
contract. See [integration notes](INTEGRATION_WITH_CURRENT_FIRMWARE.md), including complete
ESP-MQTT event reassembly for large publications. Data verification is not an ESP32/MQTT test.

## Dataset scope

- **826 windows, 2048 samples per window**, about 171 ms each at 12 kHz.
- **14 selected 2 HP recordings**, 59 non-overlapping windows each.
- Class counts: healthy 59, inner race 177, outer race 413, ball 177.
- Source IDs on the PC only: 99,107,120,132,146,159,171,187,199,211,224,236,248,260.
- No 0/1 HP raw training data and no 3 HP final-test data are packaged.
- `data/smoke_14_windows.npz` is one window per source, with IDs shared with the full replay.
  It tests plumbing quickly; it is not the full validation evaluation.

These are the same development recordings used for the current baseline result. They do
not become a new blind benchmark by being repackaged. The subset-selection rules in the
missing Additional Technical Requirements I still need confirmation. Source rates are
reference-documented; independent data-level rate confirmation remains pending.

## Files and separation

| File | Purpose |
|---|---|
| `data/validation_2hp_windows.npz` | Complete selected raw replay and opaque IDs; no labels |
| `data/smoke_14_windows.npz` | Fast raw transport/feature smoke subset |
| `data/ground_truth_PC_ONLY.csv` | Labels and source mapping, PC evaluator only |
| `data/source_preparation_manifest_PC_ONLY.json` | Source URLs/SHA256/DE keys and preparation/provenance |
| `protocol/packet_reference.py` | Binary encoder/decoder only; no MQTT connection |
| `protocol/example_window_packet.bin` | 8,248-byte reference packet for decoder testing |
| `reference/current_baseline_fp32.tflite` | Interim executed baseline, not a new training result |
| `reference/feature_reference.py`, `normalization.*` | Coherent feature reference and exported constants |
| `reference/expected_outputs_validation_PC_ONLY.npz` | Expected PC features/inputs/scores for all 826, keyed by opaque IDs |
| `reference/MODEL_ID.json` | Model hash, architecture, scope and existing development result |
| `DATA_VERIFICATION.json` | Full raw reconstruction and saved-input parity checks |
| `verify_offline.py` | Package hash, 826 packet roundtrip and PC reference-inference checks |
| `prepare_validation.py` | Reproduce raw windows from hash-verified public sources |

`PC_ONLY` is an operational separation, not an access-control or encryption claim. The PC
may store these files in this source repository. They must never be transmitted to the
ESP32 input channel. Do not send NPZ/CSV containers or expected class/score files directly.
Only the allowed packet header and raw sample bytes go to the ESP32.

## Current model status

The coherent reference is the **executed 12 -> 16 -> 8 -> 4 MLP**, 380 parameters, 36 final
epochs. Existing development validation is **825/826 correct (99.88%)**. Its FP32 TFLite
file is 3,708 bytes. Export consistency and independent PC forward-pass checks have passed.
These are model-development results, not measured deployed flash/RAM or ESP32 timings.
The newer grouped-selection guide has no executed results supplied in this handoff.

When the ML owner changes the model, replace model, feature contract, normalization,
expected outputs and model ID as a coherent version. Raw-window transport can stay stable.
No assertion is made that the future model or final 3 HP score will equal this result.

## Verification and reproduction

`python verify_offline.py` makes no network request and performs no training. It checks
package SHA256 sums, shape and opaque-ID alignment, all 826 shuffled packet roundtrips,
CRC/truncation rejection, raw feature/normalization parity, and independent NumPy inference
from the FP32 export. The generated JSON report is ignored by Git and excluded from package
SHA256 sums so it can be regenerated. This is not a LiteRT-on-device or MQTT test.

To reproduce source preparation using the original Colab package versions:

```text
python -m pip install -r requirements-prepare.txt
python prepare_validation.py --cache .cache/cwru_validation
```

Only the 14 declared 2 HP files are downloaded. SHA256 must match the recorded original
bytes before decoding. Preparation selects the exact DE key; healthy 99 uses the documented
48->12 kHz anti-alias resampling, fault sources remain at 12 kHz; 128 target-rate samples
are trimmed at each end; complete non-overlapping 2048-sample windows are retained. The
default output is `data/validation_2hp_windows.rebuilt.npz`, preserving the packaged original.
With all source files cached, add `--offline`. Original MAT files are not committed here.

The package build environment and original training versions are recorded separately.
`DATA_VERIFICATION.json` reports the actual maximum normalized-input difference against
all 826 saved inputs from the executed run, plus raw/score checks against its 14 fixtures.

## Communication teammate deliverables

Implement local broker/replay/result receiver/evaluator/dashboard integration, preserving
neutral IDs and raw data. Handle corruption, missing/truncated/duplicate/out-of-order
traffic and reconnect recovery with explicit counters. Report feature time and inference
time separately from network round-trip latency. Document the actual protocol, limits,
maintenance alert rule, versions and reproduction commands. A labeled mock/echo endpoint
may assist transport development; only real ESP32 results establish system performance.

The proposed binary packet is 8,248 application bytes, so inspect MQTT client buffer limits
and allow topic/control overhead. A broker PUBACK is not completed inference. See the
contract for deduplication, bounded queues, completion and offline behavior.

Reserved 3 HP replay is deferred until every model and optimization choice is fixed.
The project still requires 50%/80% pruning + fine-tuning, full INT8 training-only calibration,
combined pruning/INT8, and all variants measured on the same ESP32/build/replay settings.
Missing Additional Technical Requirements and new-model/device evidence remain open.
