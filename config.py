import os
import sys

def resource_path(relative_path):
    """Dapatkan path yang benar baik saat development maupun setelah di-build"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ============================================================
# DIREKTORI DASAR
# Mengambil lokasi folder tempat file ini berada secara otomatis,
# sehingga path tidak perlu ditulis manual dan bisa berjalan
# di komputer manapun (portable).
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# PATH FILE-FILE PENDUKUNG
# Semua file pendukung dicari relatif terhadap BASE_DIR,
# jadi cukup taruh file-file ini satu folder dengan program.
# ============================================================

# Path ke file model YOLO yang sudah dilatih (.pt)
MODEL_PATH = resource_path("best.pt")

# Folder tempat file log CSV hasil deteksi akan disimpan
# LOG_FOLDER tetap menggunakan BASE_DIR agar file log disimpan
# di sebelah executable, bukan di folder temporer _MEIPASS
LOG_FOLDER = os.path.join(os.path.dirname(sys.executable)
             if hasattr(sys, '_MEIPASS') else BASE_DIR, "log_file")

# Path ke file gambar logo yang tampil di GUI
LOGO_PATH = resource_path("Logo-Resmi-Unsoed.png")


# ============================================================
# PENGATURAN KAMERA / VIDEO
# ============================================================

# Sumber video: bisa diisi angka (0 = webcam utama)
# atau path ke file video seperti di bawah ini
CAMERA_INDEX = 0
#CAMERA_INDEX = "/home/teknologi-kelautan2022/Videos/Camera/7.webm"

# Lebar dan tinggi resolusi kamera dalam piksel
CAP_WIDTH  = 640
CAP_HEIGHT = 480


# ============================================================
# PENGATURAN MODEL YOLO
# ============================================================

# Batas minimum confidence score agar deteksi dianggap valid
# (0.0 - 1.0). Semakin tinggi = semakin ketat penyaringannya.
CONF_THRESH = 0.3

# Ukuran gambar input ke YOLO (piksel). Lebih kecil = lebih cepat,
# tapi akurasi bisa berkurang.
IMG_SIZE = 320

# Jalankan YOLO setiap N frame. Nilai 1 = setiap frame diproses.
# Nilai lebih besar (misal 2) = lebih ringan tapi update lebih lambat.
SKIP_N = 1


# ============================================================
# PENGATURAN TRACKER SORT
# SORT adalah algoritma pelacak objek antar frame.
# ============================================================

# Jumlah frame maksimum sebuah track boleh hilang sebelum dihapus
SORT_MAX_AGE = 5

# Jumlah frame minimum objek harus terdeteksi sebelum diberi ID resmi
SORT_MIN_HITS = 2

# Ambang batas IoU (Intersection over Union) untuk mencocokkan
# deteksi dengan track yang sudah ada (0.0 - 1.0)
SORT_IOU_THRESHOLD = 0.2


# ============================================================
# PENGATURAN GARIS PENGHITUNG
# Garis virtual vertikal yang digunakan untuk menghitung ikan
# yang melintas.
# ============================================================

# Posisi garis dalam skala 0.0 (kiri) hingga 1.0 (kanan layar)
LINE_POSITION = 0.15

# Toleransi jarak (piksel) dari garis agar crossing tidak
# terhitung dua kali akibat getaran posisi objek
LINE_OFFSET = 10


# ============================================================
# PENGATURAN GUI (TAMPILAN ANTARMUKA)
# ============================================================

# Seberapa sering tampilan diperbarui, dalam milidetik.
# Nilai 30 ms = sekitar 33 frame per detik untuk GUI.
GUI_UPDATE_MS = 30


# ============================================================
# WARNA BOUNDING BOX (FORMAT BGR - OpenCV)
# OpenCV menggunakan urutan Blue-Green-Red, bukan RGB.
# ============================================================

# Warna kotak untuk ikan yang BELUM melewati garis -> Merah
COLOR_BEFORE = (0, 0, 255)

# Warna kotak untuk ikan yang SUDAH melewati garis -> Hijau
COLOR_AFTER = (0, 255, 0)

# Warna garis penghitung virtual -> Hijau
COLOR_LINE = (0, 255, 0)