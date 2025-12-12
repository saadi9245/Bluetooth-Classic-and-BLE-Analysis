#!/usr/bin/env python3
from bluetooth import BluetoothSocket, RFCOMM
import struct, time

server_sock = BluetoothSocket(RFCOMM)
server_sock.bind(("", 3))   # channel 3
server_sock.listen(1)

print("[SERVER] Waiting for connection on RFCOMM channel 3...")
client_sock, client_info = server_sock.accept()
print("[SERVER] Accepted connection from", client_info)

try:
    while True:
        data = client_sock.recv(4096)
        if not data:
            break
        # Echo back (for RTT measurement & throughput)
        client_sock.sendall(data)
except OSError as e:
    print("[SERVER] Error:", e)

print("[SERVER] Disconnected.")
client_sock.close()
server_sock.close()

