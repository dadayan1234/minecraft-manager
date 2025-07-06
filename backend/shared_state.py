# Berisi state aplikasi yang digunakan bersama, seperti proses server yang sedang berjalan.
# Ini membantu menghindari masalah circular import.

# Key: server_id (int), Value: process (subprocess.Popen)
server_processes = {}