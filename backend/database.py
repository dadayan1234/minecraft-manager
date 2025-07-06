import sqlite3
from sqlite3 import Error

DATABASE_FILE = "user_preferences.db"

def create_connection():
    """ 
    Membuat koneksi ke database SQLite. 
    Koneksi ini akan mengembalikan baris data sebagai dictionary-like objects.
    """
    conn = None
    try:
        # check_same_thread=False diperlukan karena FastAPI bisa menggunakan thread berbeda
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        # Mengatur row_factory agar bisa mengakses kolom berdasarkan nama
        conn.row_factory = sqlite3.Row 
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
    return conn

def upgrade_users_table(conn):
    """
    Memeriksa tabel 'users' dan menambahkan kolom 'server_version' jika belum ada.
    Ini adalah cara yang aman untuk memodifikasi skema tabel yang sudah ada.
    """
    try:
        cursor = conn.cursor()
        
        # Jalankan PRAGMA untuk mendapatkan informasi kolom dari tabel users
        cursor.execute("PRAGMA table_info(users)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        # Cek apakah 'server_version' sudah ada di dalam daftar kolom
        if 'server_version' not in columns:
            print("Kolom 'server_version' tidak ditemukan, menambahkan kolom...")
            # Jika belum ada, jalankan perintah ALTER TABLE untuk menambahkannya
            cursor.execute("ALTER TABLE users ADD COLUMN server_version TEXT")
            print("Kolom 'server_version' berhasil ditambahkan.")
        
    except Error as e:
        print(f"Gagal meng-upgrade tabel users: {e}")

def create_tables(conn):
    """ 
    Membuat semua tabel yang dibutuhkan (users, user_webhooks) jika belum ada.
    """
    try:
        cursor = conn.cursor()
        
        # Skema untuk tabel pengguna
        sql_create_users_table = """ CREATE TABLE IF NOT EXISTS users (
                                        id INTEGER PRIMARY KEY,
                                        username TEXT NOT NULL UNIQUE,
                                        hashed_password TEXT NOT NULL,
                                        server_path TEXT
                                    ); """
        
        # Skema untuk tabel webhook pengguna
        sql_create_webhooks_table = """ CREATE TABLE IF NOT EXISTS user_webhooks (
                                            id INTEGER PRIMARY KEY,
                                            user_id INTEGER NOT NULL,
                                            webhook_url TEXT NOT NULL,
                                            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                                        ); """
        
        cursor.execute(sql_create_users_table)
        cursor.execute(sql_create_webhooks_table)
    except Error as e:
        print(f"Gagal membuat tabel: {e}")

def initialize_database():
    """
    Fungsi utama yang akan dipanggil saat aplikasi dimulai.
    Fungsi ini akan membuat koneksi, membuat tabel, dan meng-upgrade skema jika perlu.
    """
    conn = create_connection()
    if conn is not None:
        try:
            # 1. Buat tabel jika belum ada
            create_tables(conn)
            
            # 2. Periksa dan upgrade tabel users
            upgrade_users_table(conn)
            
            conn.commit() # Simpan semua perubahan
        finally:
            conn.close() # Pastikan koneksi selalu ditutup
    else:
        print("Error! Tidak dapat membuat koneksi database.")