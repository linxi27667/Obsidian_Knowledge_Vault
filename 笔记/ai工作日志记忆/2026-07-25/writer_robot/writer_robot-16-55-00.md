---
created: 2026-07-25 16:55:00
project: writer_robot
session: runtime-rehome-ack-lock
---

# writer_robot - runtime rehome ACK lock

## Topic

Review and repair the runtime rehome recovery path after STOP, disconnect, or execution failure.

## Fix

### `write_robot/TASK/writer_cloud.c`

`needs_rehome` was cleared before the final `rehome completed` ACK was known to be queued. If AT/UART transmission setup failed, a new job could be accepted without the required completion ACK.

The handler now restores `needs_rehome=true` whenever scheduling that final ACK fails. The success ACK still reports `needs_rehome:false`; only a successfully queued final ACK unlocks the device.

## Verification

- MSPM0 protocol host tests: 88 checks passed.
- Web backend: 26 tests passed.
- Web frontend: Vitest passed; production build passed.
- Xiaozhi host tests: 11 tests passed.
- MSPM0 Keil rebuild: 0 errors, 0 warnings; `RW+ZI=32352 B`, 416 B remains in 32 KiB.
- Xiaozhi ESP-IDF build passed; app partition has 36% free.
- Docker services are running; `/healthz` returned `ok=true`, `mqtt_connected=true`, `fonts=5`.

## Remaining Hardware Validation

No firmware was flashed and no motor motion, ESP-01S transport, serial/RTT capture, or physical rehome cycle was performed. Verify STOP, disconnect abort, limit timeout, final completed ACK, and post-rehome job acceptance with pen removed on a controlled bench.
