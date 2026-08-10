import config
from detector import FishDetector
from logger import FishLogger
from gui import FishCounterGUI


def main():
    """
    Fungsi utama program. Menginisialisasi semua komponen dan menjalankan GUI.

    Urutan pembuatan komponen:
      1. FishDetector — mendeteksi dan melacak ikan lewat YOLO + SORT
      2. FishLogger   — mencatat data deteksi ke file CSV
      3. FishCounterGUI — menampilkan antarmuka grafis dan menghubungkan
                          detector serta logger ke tombol-tombol kontrol

    Ketiganya menerima 'config' sebagai sumber pengaturan bersama,
    sehingga cukup ubah nilai di config.py untuk mengubah perilaku program.
    """

    # Buat objek detektor: memuat model YOLO dan menyiapkan tracker SORT
    detector = FishDetector(config)

    # Buat objek logger: menyiapkan buffer untuk pencatatan data CSV
    logger = FishLogger(config)

    # Buat antarmuka grafis dan hubungkan dengan detektor dan logger
    app = FishCounterGUI(config, detector, logger)

    # Jalankan GUI — program akan berjalan di sini hingga jendela ditutup
    app.run()


# ============================================================
# Blok ini memastikan main() hanya dipanggil jika file ini
# dijalankan langsung (bukan di-import oleh file lain).
# Ini adalah konvensi standar Python untuk file entry point.
# ============================================================
if __name__ == "__main__":
    main()