# Integration with the current ESP32 bridge

The current `firmware/mqtt_bridge/main/mqtt_bridge.c` is a plain-text connectivity smoke
test. It subscribes to `mct462/test/from_pc`; exactly `Hello ESP32` produces `Hello PC`
on `mct462/test/from_esp32`. Wi-Fi and broker parameters are set through its Kconfig.
The bridge does not yet implement raw windows, CRC, IDs, feature extraction, normalization,
inference, result timing, deduplication or the proposed v1 status/result/error schema.

This handoff adds data and reference code, not a firmware implementation. Keep the existing
hello test as a connectivity milestone. Agree and implement the proposed protocol with the
ESP32 owner; changing topic names alone will not make the existing bridge compatible.

## Large receive messages

The v1 application packet is 8248 bytes: a 52-byte header, 8192 raw-sample bytes and a
4-byte CRC32 trailer. ESP-MQTT can deliver a single MQTT publication through several
`MQTT_EVENT_DATA` callbacks. Reassemble bounded data using `total_data_len` and
`current_data_offset`, noting that the topic is supplied only for the first callback.
Alternatively, explicitly configure and verify a receive buffer that holds the publication.
Only validate/decode/infer once a complete publication has arrived. Do not treat each callback
as a complete raw window. This library receive chunking is distinct from application-level
fragmentation; the proposed v1 format still uses one MQTT publication per raw window.

Reject oversize/incomplete/malformed messages with counters and errors rather than copying
beyond a bounded buffer. Keep MQTT/event handling responsive while feature extraction and
inference run through an agreed queue/task interface. Measure actual ESP32 memory and times.

## Implement and verify

1. Establish the existing text echo over the local broker first.
2. Test `protocol/example_window_packet.bin` against the reference decoder.
3. Implement complete-packet validation, opaque IDs and CRC; then process the 14-window smoke set.
4. Integrate the feature function, matching normalization and matching model as one version.
5. Return actual class/confidence and separate feature/inference times with matching IDs.
6. Run all 826 raw validation windows, joining the separate truth map on the PC only.
7. Exercise invalid, duplicate, missing, late/out-of-order and reconnect scenarios; document policies.

Record exact ESP-IDF and MQTT component versions. The current component declaration permits
a broad IDF range and an unpinned MQTT dependency; the actual tested build must be reproducible.
No ESP32 build, MQTT interoperability or deployed performance is claimed by this data commit.

Reference: [Espressif ESP-MQTT event documentation](https://raw.githubusercontent.com/espressif/esp-mqtt/master/include/mqtt_client.h).
