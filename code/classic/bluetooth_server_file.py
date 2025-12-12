import bluetooth
import time

server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
server_sock.bind(("", bluetooth.PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]
bluetooth.advertise_service(server_sock, "BTFileServer",
                            service_classes=[bluetooth.SERIAL_PORT_CLASS],
                            profiles=[bluetooth.SERIAL_PORT_PROFILE])

print(f"[SERVER] Waiting for connection on RFCOMM channel {port}...")
client_sock, client_info = server_sock.accept()
print(f"[SERVER] Accepted connection from {client_info}")

with open("received_file", "wb") as f:
    start = time.time()
    total_bytes = 0
    while True:
        data = client_sock.recv(1024)
        if not data:
            break
        f.write(data)
        total_bytes += len(data)
    end = time.time()

duration = end - start
throughput = total_bytes / duration / 1024  # KB/s
print(f"[SERVER] Received {total_bytes} bytes in {duration:.2f}s ({throughput:.2f} KB/s)")

client_sock.close()
server_sock.close()
