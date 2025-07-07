import time
import threading
from backend.shared_state import server_processes

# Menyimpan waktu terakhir ada aktivitas untuk setiap server
# Key: server_id, Value: timestamp
last_activity = {}
IDLE_TIMEOUT_MINUTES = 5 # Server akan mati setelah 5 menit idle

def update_activity(server_id: int):
    """Panggil fungsi ini setiap kali ada aktivitas di server (misal, command atau player join)."""
    last_activity[server_id] = time.time()

def watcher_thread_func():
    """Fungsi yang akan berjalan di thread terpisah untuk memonitor server."""
    print("Watcher server idle dimulai...")
    while True:
        # Buat salinan untuk menghindari masalah saat iterasi
        current_processes = server_processes.copy()
        
        for server_id, process in current_processes.items():
            # Cek jika proses masih berjalan
            if process.poll() is None:
                # Jika tidak ada aktivitas yang tercatat, catat sekarang
                if server_id not in last_activity:
                    update_activity(server_id)
                    continue

                # Cek selisih waktu
                idle_duration = time.time() - last_activity[server_id]
                if idle_duration > IDLE_TIMEOUT_MINUTES * 60:
                    print(f"Server {server_id} telah idle selama lebih dari {IDLE_TIMEOUT_MINUTES} menit. Mematikan...")
                    try:
                        process.stdin.write("stop\n")
                        process.stdin.flush()
                        # Hapus dari daftar agar tidak dicek lagi
                        server_processes.pop(server_id, None)
                        last_activity.pop(server_id, None)
                    except Exception as e:
                        print(f"Gagal mematikan server idle {server_id}: {e}")
            else:
                # Jika proses sudah mati, bersihkan dari daftar
                server_processes.pop(server_id, None)
                last_activity.pop(server_id, None)
        
        # Cek setiap 30 detik
        time.sleep(30)

def start_watcher():
    """Memulai thread watcher."""
    watcher = threading.Thread(target=watcher_thread_func)
    watcher.daemon = True # Thread akan mati saat aplikasi utama berhenti
    watcher.start()