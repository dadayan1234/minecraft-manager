
# 🎮 Minecraft Server Manager

Sebuah panel kontrol web modern untuk mengelola server Minecraft **Aternos** Anda dari jarak jauh. Dilengkapi dengan antarmuka yang bersih, manajemen file, dan integrasi canggih seperti Ngrok tunnel dan notifikasi webhook Discord.

![Screenshot Panel](https://i.imgur.com/uG9XlAM.png)

## ✨ Hal Menarik dari Proyek Ini

Repositori ini bukan sekadar skrip untuk menyalakan server, tetapi sebuah solusi manajemen lengkap yang memiliki beberapa keunggulan unik:

* **Manajemen Terpusat**: Anda tidak perlu lagi membuka banyak tab. Semua kebutuhan mulai dari menyalakan server, melihat konsol, mengirim perintah, mengelola file, hingga membuat tunnel publik ada dalam satu dasbor.
* **Integrasi Ngrok Bawaan**: Lupakan kerumitan port forwarding. Dengan sekali klik, panel ini akan membuat tunnel publik menggunakan Ngrok, memungkinkan teman-teman Anda terhubung ke server lokal dengan mudah.
* **Notifikasi Tunnel ke Discord**: Ini adalah fitur andalan. Setiap kali tunnel Ngrok berhasil dibuat dan mendapatkan alamat publik baru, panel akan **secara otomatis mengirimkan notifikasi ke channel Discord** Anda melalui webhook. Para pemain bisa langsung mendapatkan alamat server terbaru tanpa Anda perlu menyalin dan menempelkannya secara manual.

---

## 🚀 Fitur Utama

* **Kontrol Server**: Start, Stop, dan Restart server Aternos Anda.
* **Konsol Real-time**: Pantau log server secara langsung melalui WebSocket.
* **Eksekusi Perintah**: Kirim perintah langsung ke konsol server dari web.
* **Manajer File**:
    * Upload file dan plugin.
    * Download file atau seluruh direktori sebagai file `.zip`.
    * Rename dan hapus file/folder.
    * Pratinjau file teks.
* **Manajer Tunnel Ngrok**: Start dan Stop tunnel Ngrok untuk server Anda.
* **Editor Konfigurasi**: Ubah `server.properties` langsung dari antarmuka web.
* **Antarmuka Modern**: UI yang bersih, responsif, dan dilengkapi dengan tema terang/gelap.

---

## 💬 Bergabunglah dengan Komunitas Kami!

Punya pertanyaan, saran, butuh bantuan, atau ingin sekadar berbagi pengalaman? Bergabunglah dengan server Discord kami! Kami sangat senang jika Anda mau menjadi bagian dari komunitas.

[![Join our Discord](https://discordapp.com/api/guilds/1122733972230447124/widget.png?style=banner2)](https://discord.gg/9wc4ktqE8Q)

---

## 🛠️ Instalasi dan Konfigurasi

Ikuti langkah-langkah berikut untuk menjalankan panel kontrol ini di komputer Anda.

### 1. Prasyarat

* Python 3.8 atau lebih baru
* Akun [Ngrok](https://ngrok.com/) (untuk mendapatkan authtoken)

### 2. Instalasi

Clone repositori ini dan install semua dependensi yang dibutuhkan.

```bash
# 1. Clone repositori
git clone [https://github.com/dadayan1234/minecraft-manager.git](https://github.com/dadayan1234/minecraft-manager.git)

# 2. Masuk ke direktori proyek
cd minecraft-manager

# 3. Install dependensi Python
pip install -r requirements.txt
```
---

📄 Lisensi
Repositori ini tidak memiliki lisensi spesifik. Anda bebas untuk menggunakan dan memodifikasinya untuk keperluan pribadi. Namun, disarankan untuk menambahkan lisensi sumber terbuka seperti MIT License jika Anda berencana untuk mengembangkannya lebih lanjut.
