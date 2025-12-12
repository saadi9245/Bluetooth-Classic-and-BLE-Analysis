import bluetooth
import time

# Change filename to send
#filename = "/home/pi/ressources/image.jpg"
filename = "/home/pi/ressources/text.txt"
# filename = "/home/pi/ressources/video.mp4"
# filename = "/home/pi/ressources/music.mp3"




target_name = "raspi-b"  # Adapt to device name
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

with open(filename, "rb") as f:
    print(f"[CLIENT] Sending file: {filename}")
    start = time.time()
    total_bytes = 0
    while chunk := f.read(1024):
        sock.send(chunk)
        total_bytes += len(chunk)
    end = time.time()

duration = end - start
throughput = total_bytes / duration / 1024  # KB/s
print(f"[CLIENT] Sent {total_bytes} bytes in {duration:.2f}s ({throughput:.2f} KB/s)")

sock.close()
