#!/usr/bin/env python3
from bluetooth import BluetoothSocket, RFCOMM
import time, struct, csv, secrets, statistics, datetime

server_mac = "2C:CF:67:27:F7:11"   # MAC du Pi serveur

# Config
THROUGHPUT_DURATION = 60     # durée en secondes pour le test débit
PAYLOAD_SIZE = 1024          # taille des paquets (octets) pour débit
LATENCY_PINGS = 200          # nombre de pings pour latence/jitter
LAT_PAYLOAD = 64             # taille des paquets pour latence

# Connection to RFCOMM server on channel 3
print("[CLIENT] Connecting to", server_mac)
sock = BluetoothSocket(RFCOMM)
sock.connect((server_mac, 3))
print("[CLIENT] Connected.")

# ---------- THROUGHPUT TEST ----------
# Create random packet, initialize counters send/received, start timer
print("[CLIENT] Starting throughput test...")
buf = secrets.token_bytes(PAYLOAD_SIZE)
sent = recv = 0
t0 = time.time()
t_end = t0 + THROUGHPUT_DURATION


timestamp = datetime.datetime.now().strftime("%d%m_%H%M")
throughput_file = f"throughput_{timestamp}.csv"
latency_file = f"latency_{timestamp}.csv"


with open(throughput_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["t_s","sent_bytes","recv_bytes"])
    # Send packet then read echo bounced by server
    while time.time() < t_end:
        sock.sendall(buf)
        sent += len(buf)
        echo = sock.recv(len(buf))
        recv += len(echo)
        # Write in CSV progression octets send/received for throughput tracking in time
        writer.writerow([f"{time.time()-t0:.6f}", sent, recv])

dt = time.time()-t0
mbit_s = (recv*8)/1e6/dt
print(f"[CLIENT] Throughput: {mbit_s:.2f} Mbit/s over {dt:.2f}s")

# ---------- LATENCY TEST ----------
print("[CLIENT] Starting latency test...")
fmt = "!d"  # double (8 octets)
pad = b"x" * max(0, LAT_PAYLOAD-8)
results = []
losses = 0

with open(latency_file,"w",newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["seq","rtt_ms"])
    for i in range(LATENCY_PINGS):
        # Send packet with send time then wait for echo
        ts = time.monotonic()
        pkt = struct.pack(fmt, ts)+pad
        sock.sendall(pkt)
        try:
            echo = sock.recv(len(pkt))
        except OSError:
            losses += 1
            continue
        if len(echo) != len(pkt):
            losses += 1
            continue
        ts2 = time.monotonic()
        # Calcule le Round-Trip Time (RTT) en millisecondes. Calculate Round-Trip Time (RTT) in ms
        rtt = (ts2-ts)*1000.0
       # Store each RTT in a list and CSV for analysis
        results.append(rtt)
        writer.writerow([i, f"{rtt:.3f}"])
# ---------- ANALYSE ----------
if results:
        # Give necessary metrics mean/median/jitter
        mean = statistics.mean(results)
        median = statistics.median(sorted(results))
        stdev = statistics.pstdev(results)
        # Calculate 95th/99th percentiles to show the “worst” observed latencies
        p95 = statistics.quantiles(results, n=100)[94]
        p99 = statistics.quantiles(results, n=100)[98]
        print(f"[CLIENT] Latency mean={mean:.2f} ms median={median:.2f} ms p95={p95:.2f} ms p99={p99:.2f} ms jitter={stdev:.2f} ms losses={losses}")
else:
    print("[CLIENT] No latency samples collected.")

sock.close()
print(f"[CLIENT] Finished. CSV files written: {throughput_file}, {latency_file}")
