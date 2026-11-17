# Proposed PC/ESP32 communication contract v1

This contract is a team proposal, not wording copied from the project brief. The missing
Additional Technical Requirements IV may prescribe more detailed error policies. Reconcile
this contract with those rules and agree it with the ESP32 owner before final integration.

## Flow and scope

PC reads prepared raw windows -> local MQTT broker -> ESP32 validates packet -> ESP32
extracts features, normalizes and performs inference -> MQTT result -> PC evaluator and
dashboard. Internet/cloud services are not needed during operation. A local Mosquitto
broker is one free option; record exact client/broker versions and configuration.

Model input is 12 normalized features, but network input is **raw** 2048-sample windows.
The communication sender must preserve raw sample values and ordering; it must not
precompute features, standardize windows or resample these already-prepared 12 kHz inputs.
Firmware feature extraction belongs at the ESP32 and must match the ML contract.

## Data scope

`data/validation_2hp_windows.npz` contains `samples` with shape (826,2048), float32
little-endian, and `window_ids` with shape (826,), opaque UUIDs. These are all prepared
windows from the currently selected 14 development-validation recordings at 2 HP, 59 per
recording. `data/smoke_14_windows.npz` is one window per source for fast plumbing checks.
The smoke subset shares IDs with the full dataset; run it as a separate replay session.
Neither file contains training or 3 HP final-test data, and neither is a newly blind test.
On each new run, choose a fresh run UUID, shuffle windows and assign sequence numbers AFTER
shuffling. On a retry retain the same run/window ID, sequence and sample bytes.

`data/ground_truth_PC_ONLY.csv` is private PC evaluation metadata. Original source IDs,
class labels/names, load, source filenames and fault size/position must never be transmitted
to ESP32 in messages, topics or identifiers. Do not transmit the NPZ/CSV containers themselves;
encode only allowed packet fields and raw sample bytes.

## Neutral topics, proposed

- `mct462/v1/esp32/window`: input binary packets; retain false.
- `mct462/v1/esp32/result`: actual model results; retain false.
- `mct462/v1/esp32/error`: explicit input/processing errors; retain false.
- `mct462/v1/esp32/status`: status/heartbeat and offline Last Will; retained status allowed.

The fixed `esp32` segment identifies the device, not a class. Keep class-dependent data out
of input topics. Predicted class information is allowed in output results.

## Binary input packet, 8248 bytes total

Header uses Python struct `<4sBBH16s16sIII`, exactly 52 bytes:

| Offset | Bytes | Field |
|---|---:|---|
| 0 | 4 | Magic ASCII `M462` |
| 4 | 1 | Protocol version = 1 |
| 5 | 1 | Flags = 0 |
| 6 | 2 | Reserved = 0, uint16 little-endian |
| 8 | 16 | Run UUID, binary UUID bytes |
| 24 | 16 | Opaque window UUID, binary UUID bytes |
| 40 | 4 | Sequence, uint32 little-endian, assigned after shuffling |
| 44 | 4 | Sample rate, uint32 little-endian = 12000 |
| 48 | 4 | Sample count, uint32 little-endian = 2048 |
| 52 | 8192 | Samples, 2048 IEEE754 float32 little-endian, in time order |
| 8244 | 4 | CRC32 little-endian of the preceding 8244 bytes |

CRC convention: standard IEEE CRC32 as produced by Python `zlib.crc32(header+samples)
& 0xffffffff`. This covers the header and sample bytes. It does not include the trailer.
The reference codec and example packet allow an independent byte-for-byte decoder check.
Read fields explicitly instead of relying on a compiler's native struct packing/alignment.

Allow MQTT topic/control overhead beyond the 8248 application bytes. Verify client receive
buffers and RAM. A 16 KiB MQTT buffer is a plausible starting configuration to measure,
not a guarantee of device resource fit. PubSubClient's current default packet buffer is
256 bytes; it must be enlarged if used for these full-window packets. It also has API/QoS
capabilities that must be checked when choosing the firmware client. Fragmentation is not
used in this proposed v1; if required, both ends need a new documented reassembly protocol.

## Results

Publish JSON with matching `run_id`, `window_id`, `sequence`, protocol `version`, a model
identifier/hash, `status`, `predicted_class` integer 0..3, `confidence` float in [0,1],
`feature_us` and `inference_us` as nonnegative measured times in microseconds. Class order:
0 healthy; 1 inner race; 2 outer race; 3 ball. Confidence is the largest softmax score.
Measure feature extraction and inference separately on the ESP32. The PC measures round-trip
latency separately; it cannot substitute for those timings. No example values in this
document are claims of actual device measurements.

On an input error, publish a reject/error event, not a fabricated prediction. Include
identifiers only if safely decoded; specify reason codes (bad length, CRC, version,
count/rate, non-finite data, overflow, inference error). Invalid packets do not enter inference.

## Reliability and counters

Start with a bounded queue and one in-flight window. Make send rate, result deadline,
retry limit and dedup-cache size configurable. QoS 1 is a reasonable requested transport
choice where supported, but duplicates remain possible and broker PUBACK is not completion
of ESP32 inference. Application results/errors acknowledge completion. Document the actual
QoS used in each direction if the selected client does not support requested QoS.

Deduplicate by (run_id, window_id). Count a valid classification only once, and define
whether duplicate inputs return a cached result or explicit duplicate acknowledgement.
Keep all counters consistent under retries and duplicate results. Handle late/out-of-order
messages explicitly; use expected ID sets and sequence tracking to distinguish missing
windows from later arrivals. Exact policies/deadlines are proposed until Additional IV is known.

On Wi-Fi/broker loss, show offline status, stop issuing new windows to an unavailable node,
reconnect automatically and resume/retry pending IDs according to the documented policy.
Do not count retransmission attempts as extra dataset examples. Keep reconnect, reject,
duplicate, timeout, missing, late/out-of-order and unique-result counters.

## PC evaluator and dashboard

The PC joins unique results with the PC-only truth map. Report classification metrics for
the evaluated unique windows, alongside completion/missing/reject counts so accuracy does
not hide delivery failures. Display online/offline status, current prediction/confidence,
history, per-class counts, maintenance state, both processing times, message counters and
achieved unique windows/second. A documented maintenance rule can use a rolling majority;
its parameters, false alerts and delay must be measured. It must use predictions, not truth.

## Demonstrations to deliver

1. Local broker + PC sender/subscriber + ESP32 connected on LAN.
2. Correct decoding/CRC of the supplied binary fixture, then the 14-window smoke subset and full 826-window replay in shuffled order.
3. Real ESP32 feature/model results joined to PC labels, with separate measured timings.
4. Deliberate corrupt, truncated, duplicate, omitted and out-of-order traffic, with correct counters.
5. Wi-Fi interruption and broker restart, automatic recovery and controlled pending-window handling.
6. Internet disconnected while local Wi-Fi remains active; full local flow still works.
7. Logs/CSV plus dashboard evidence, source repository and exact reproduction instructions.

Transport development may begin with an explicitly labeled echo/mock endpoint. Only real
ESP32 inference counts as measured model/system performance. The full currently selected validation replay is included; confirm its subset rules
before claiming compliance. Reserve 3 HP final replay until all model/optimization choices are fixed.

Sources: project brief requirements I-IV, XI-XIV and design constraints;
[Mosquitto](https://mosquitto.org/),
[OASIS MQTT 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html),
[PubSubClient source/buffer setting](https://github.com/knolleary/pubsubclient/blob/master/src/PubSubClient.h).

## Current repository integration note

The existing firmware is a text echo implementation, not a v1 decoder. See
`../INTEGRATION_WITH_CURRENT_FIRMWARE.md`. ESP-MQTT can split one publication among DATA
events (`total_data_len`, `current_data_offset`; first-event topic only). Bounded complete
publication reassembly, or a verified sufficient receive-buffer configuration, is required
before decoding the 8248-byte v1 packet. This is not application-level v1 fragmentation.
