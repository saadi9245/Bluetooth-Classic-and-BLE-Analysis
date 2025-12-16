#!/usr/bin/env python3
import bluetooth
import time
import secrets

# ----------------------------
# Scenario 1 settings (random payload)
# ----------------------------
TOTAL_BYTES = 1_000_000   # change this (e.g., 50_000, 1_048_576, 5_000_000, ...)
CHUNK_SIZE = 1024

target_name = "raspi-b"   # Adapt to device name
target_address = None

print("[CLIENT] Searching for server...")
nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True)
for addr, name in nearby_devices:
    if name == target_name:
        target_address = addr
        break

if target_address is None:
    print("[CLIENT] Could not find target device.")
    exit()

print(f"[CLIENT] Connecting to {target_address}...")
sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
sock.connect((target_address, 1))

print(f"[CLIENT] Sending random payload: {TOTAL_BYTES} bytes")
start = time.time()
total_bytes = 0
remaining = TOTAL_BYTES

while remaining > 0:
    n = CHUNK_SIZE if remaining >= CHUNK_SIZE else remaining
    chunk = secrets.token_bytes(n)     # random bytes
    sock.send(chunk)
    total_bytes += n
    remaining -= n

end = time.time()

duration = end - start if end > start else 1e-9
throughput = total_bytes / duration / 1024  # KB/s
print(f"[CLIENT] Sent {total_bytes} bytes in {duration:.2f}s ({throughput:.2f} KB/s)")

sock.close()
