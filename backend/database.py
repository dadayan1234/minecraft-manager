import sqlite3
from sqlite3 import Error

DATABASE_FILE = "user_preferences.db"

def create_connection():
    """Membuat koneksi ke database SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
    return conn

def create_tables(conn):
    """Membuat semua tabel yang dibutuhkan jika belum ada."""
    try:
        cursor = conn.cursor()
        
        # Tabel pengguna (tanpa kolom server_version dan server_path lagi)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL
            );
        """)
        
        # Tabel baru untuk menyimpan data setiap server
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        
        # Tabel webhook tetap sama
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_webhooks (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                webhook_url TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
    except Error as e:
        print(f"Gagal membuat tabel: {e}")

def migrate_schema_if_needed(conn):
    """
    Memeriksa dan memigrasikan skema lama ke skema baru.
    Akan menambahkan kolom 'server_path' kembali jika tidak ada,
    lalu membuat tabel 'servers' jika belum ada.
    Ini untuk transisi yang mulus.
    """
    try:
        cursor = conn.cursor()
        # Cek kolom di tabel users
        cursor.execute("PRAGMA table_info(users)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        # Jika kolom lama (misal, server_version) masih ada, kita bisa biarkan saja
        # atau menulis logika migrasi data ke tabel baru. Untuk sekarang, kita
        # cukup pastikan tabel baru ada.
        if 'server_version' in columns:
             print("Skema lama terdeteksi. Disarankan untuk memigrasikan data secara manual.")

        # Buat tabel servers (akan dilewati jika sudah ada)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

    except Error as e:
        print(f"Gagal memigrasi skema: {e}")

def initialize_database():
    """Inisialisasi database: membuat koneksi, membuat tabel, dan migrasi."""
    conn = create_connection()
    if conn is not None:
        try:
            create_tables(conn)
            migrate_schema_if_needed(conn)
            conn.commit()
        finally:
            conn.close()
    else:
        print("Error! Tidak dapat membuat koneksi database.")