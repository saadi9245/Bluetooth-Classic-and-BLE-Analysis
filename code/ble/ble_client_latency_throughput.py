# ble_perf_client_final.py (Sur raspi-a)
import pexpect
import time
import sys
import os
import math

# --- CONFIGURATION ---
SERVER_ADDRESS = "2C:CF:67:27:F7:11" 
# NOTE: Le même handle 0x0014 est utilisé pour les deux tests.
HANDLE_WRITE_AND_RTT = "0x0014" 

# Fichier et réglages
FILE_SIZE_MB = 1
FILENAME = "test_data.bin"
LATENCY_PACKET_SIZE = 10
LATENCY_TEST_COUNT = 50 
MAX_WRITE_CHUNK_SIZE = 50 

TIMEOUT_S = 15 
GATTTOOL_PROMPT = r'\[.{17}\]\[LE\]>' 

# --- STATE ---
RTT_RESULTS = []

# --- FONCTIONS GATTTOOL ---

def create_dummy_file(filename, size_mb=1):
    """Création du fichier factice."""
    
    # CONVERSION ENTIÈRE FORCÉE
    # size_bytes doit être un entier
    size_bytes = int(size_mb * 1024 * 1024) 
    
    if not os.path.exists(filename) or os.path.getsize(filename) != size_bytes:
        print(f"[{time.strftime('%H:%M:%S')}] Création du fichier factice: {filename} ({size_bytes} octets)...")
        with open(filename, 'wb') as f:
            # size_bytes est garanti d'être un entier ici
            f.write(os.urandom(size_bytes))
        print(f"[{time.strftime('%H:%M:%S')}] Fichier créé.")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] Utilisation du fichier existant: {filename}.")

def connect_gatttool():
    """Établit la connexion gatttool en mode interactif."""
    print(f"[{time.strftime('%H:%M:%S')}] Démarrage de la connexion interactive vers {SERVER_ADDRESS}...")
    
    try:
        child = pexpect.spawn(
            f'sudo gatttool -b {SERVER_ADDRESS} -I -t random', 
            timeout=TIMEOUT_S
        )
        child.expect(r'\[.+\]\s*') 
        child.sendline('connect')
        child.expect(GATTTOOL_PROMPT, timeout=TIMEOUT_S)
        print(f"[{time.strftime('%H:%M:%S')}] [SUCCESS] Connexion établie.")
        return child

    except Exception as e:
        print(f"\n[{time.strftime('%H:%M:%S')}] [ERROR] Échec de la connexion. Vérifiez 'advertise on'. Erreur: {e}")
        return None

def run_latency_test(child):
    global RTT_RESULTS
    RTT_RESULTS = []
    print(f"\n[{time.strftime('%H:%M:%S')}] --- STARTING LATENCY TEST (RTT) ---")
    
    # 1. Boucle de test RTT
    for i in range(LATENCY_TEST_COUNT):
        payload = os.urandom(LATENCY_PACKET_SIZE).hex()
        
        sys.stdout.write(f"\r[{time.strftime('%H:%M:%S')}] Latency Test: {i+1}/{LATENCY_TEST_COUNT} packets...")
        sys.stdout.flush()

        # Utilisation de char-write-REQ (Latence fonctionne et RTT est mesurable)
        time_start_rtt = time.time()
        child.sendline(f'char-write-req {HANDLE_WRITE_AND_RTT} {payload}')
        
        # Attendre le message de confirmation de gatttool
        try:
            child.expect(r'Characteristic value was written successfully|' + GATTTOOL_PROMPT, timeout=2) 
            time_end_rtt = time.time()
            
            rtt = (time_end_rtt - time_start_rtt) * 1000 
            RTT_RESULTS.append(rtt)
                
        except pexpect.exceptions.Timeout:
            print(f"\n[WARN] RTT timeout for packet {i+1}.")
            
        time.sleep(0.01) # Petit délai entre les paquets
        
    # 2. Afficher les résultats
    if RTT_RESULTS:
        avg_rtt = sum(RTT_RESULTS) / len(RTT_RESULTS)
        min_rtt = min(RTT_RESULTS)
        max_rtt = max(RTT_RESULTS)
        print(f"\n[{time.strftime('%H:%M:%S')}] --- LATENCY TEST COMPLETE ---")
        print(f"  Total Valid RTTs: {len(RTT_RESULTS)} / {LATENCY_TEST_COUNT}")
        print(f"  Average RTT: {avg_rtt:.3f} ms")
        print(f"  Min RTT: {min_rtt:.3f} ms")
        print(f"  Max RTT: {max_rtt:.3f} ms")
        print("------------------------------")
    else:
        print("\n[FAIL] Aucune réponse RTT valide reçue.")


def run_throughput_test(child):
    print(f"\n[{time.strftime('%H:%M:%S')}] --- STARTING THROUGHPUT TEST ---")
    print(f"[WARN] Ce test utilise char-write-req pour la fiabilité et prendra environ 17 minutes pour {FILE_SIZE_MB} MB.")

    file_size = FILE_SIZE_MB * 1024 * 1024
    
    # 1. Envoyer le signal de début de transfert
    child.sendline(f'char-write-req {HANDLE_WRITE_AND_RTT} {b"START_TRANSFER".hex()}')
    child.expect(GATTTOOL_PROMPT, timeout=5)
    
    start_time = time.time()
    bytes_sent = 0
    max_payload_size = MAX_WRITE_CHUNK_SIZE 
    
    try:
        with open(FILENAME, 'rb') as f:
            while True:
                chunk = f.read(max_payload_size)
                if not chunk:
                    break
                
                # Utilisation de char-write-REQ (lent, mais fonctionne)
                child.sendline(f'char-write-req {HANDLE_WRITE_AND_RTT} {chunk.hex()}') 
                
                # Attendre la confirmation après chaque paquet (cause la lenteur)
                child.expect(r'Characteristic value was written successfully|' + GATTTOOL_PROMPT, timeout=10) 
                
                bytes_sent += len(chunk)
                
                if bytes_sent % (1024 * 100) < len(chunk): 
                    sys.stdout.write(f"\r[{time.strftime('%H:%M:%S')}] Sending: {bytes_sent / 1024:.2f} KB / {file_size / 1024:.2f} KB...")
                    sys.stdout.flush()

        # 2. Envoyer le signal de fin de transfert
        child.sendline(f'char-write-req {HANDLE_WRITE_AND_RTT} {b"END_TRANSFER".hex()}')
        child.expect(GATTTOOL_PROMPT, timeout=5)

        end_time = time.time()
        duration = end_time - start_time
        
        throughput = (bytes_sent / 1024) / duration if duration > 0 else 0
        
        print(f"\n[{time.strftime('%H:%M:%S')}] --- THROUGHPUT TEST COMPLETE ---")
        print(f"  Total Bytes Sent: {bytes_sent} bytes")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Client Throughput: {throughput:.2f} KB/s")
        print("------------------------------")

    except Exception as e:
        print(f"\n[{time.strftime('%H:%M:%S')}] Throughput test failed (Timeout likely): {e}")


# --- MAIN ---

def disconnect_and_exit(child):
    if child and child.isalive():
        print(f"\n[{time.strftime('%H:%M:%S')}] Déconnexion...")
        try:
            child.sendline('exit')
            child.expect(pexpect.EOF, timeout=5)
        except Exception:
            child.close()
    print(f"[{time.strftime('%H:%M:%S')}] Programme terminé.")


def main():
    create_dummy_file(FILENAME, size_mb=FILE_SIZE_MB) 
    
    gatt_session = connect_gatttool()

    if gatt_session:
        # Les deux tests sont maintenant exécutés dans le même script
        run_latency_test(gatt_session)
        run_throughput_test(gatt_session)
        
        disconnect_and_exit(gatt_session)
    else:
        print(f"[{time.strftime('%H:%M:%S')}] Échec de la connexion. Impossible de continuer les tests.")


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Veuillez exécuter le script avec sudo (ex: sudo python3 ble_perf_client_final.py)")
        sys.exit(1)
        
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%H:%M:%S')}] Arrêté par l'utilisateur.")
    except Exception as e:
        print(f"\n[{time.strftime('%H:%M:%S')}] Une erreur fatale est survenue: {e}")
