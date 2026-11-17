I added the complete communication handoff under `communication/`.

- `data/validation_2hp_windows.npz` contains all 826 prepared raw validation windows from
  our selected 14 recordings at 2 HP. Each window has 2048 float32 samples at 12 kHz.
- `data/smoke_14_windows.npz` is just a quick 14-window subset; it is not the full replay.
- The CSV and files marked `PC_ONLY` hold labels, source metadata and expected results for
  the PC evaluator. Never transmit these to the ESP32 or encode them in MQTT topics/IDs.
- Protocol examples, a codec, source/preparation hashes, offline verification and the coherent
  interim FP32 model/feature/normalization references are included. No training or 3 HP
  final-test raw data is included.

Start with `communication/README.md`. From that folder, install `requirements.txt` and run
`python verify_offline.py`. Shuffle replay and send raw samples unchanged with opaque IDs;
the ESP32 computes features and normalization. Start with the smoke subset, then all 826.

Our current firmware still only exchanges `Hello ESP32` / `Hello PC`. Read
`INTEGRATION_WITH_CURRENT_FIRMWARE.md` and agree the proposed v1 contract before implementing
both ends, including reassembly of large ESP-MQTT receive events. Return actual predictions,
confidence, matching IDs and separately measured feature/inference times. Add deduplication,
error counters, reconnect handling, logging and dashboard integration.

This is development validation and integration input, not a final-test or ESP32 performance
claim. The grouped-training guide has no executed results supplied here; the included model
is the audited interim 380-parameter baseline. Keep 3 HP reserved for the final evaluation.
