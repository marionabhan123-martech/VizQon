import os
import time
import datetime
import threading


class FishLogger:
    """
    Kelas yang bertanggung jawab mencatat data deteksi ke file TXT.

    Cara kerjanya:
      - Berjalan di thread terpisah agar tidak mengganggu deteksi dan GUI
      - Setiap 1 detik, dicatat satu baris snapshot kondisi:
        timestamp, count_total, fps_loop, fps_yolo
      - Data disimpan di memori dahulu, baru ditulis ke file TXT saat
        pengguna menekan tombol STOP RECORD
    """

    def __init__(self, config):
        """
        Inisialisasi logger. Dipanggil satu kali saat program dimulai.

        Parameter:
            config : modul config.py yang berisi LOG_FOLDER dan pengaturan lain
        """

        self.config     = config
        self.log_folder = config.LOG_FOLDER   # folder tujuan penyimpanan CSV

        # Tempat menampung semua baris data sebelum ditulis ke file
        # Setiap elemen adalah satu baris: [frame, id, conf, x1, x2, ...]
        self.log_rows = []

        # Menyimpan nomor frame terakhir yang sudah dicatat,
        # digunakan untuk menghindari pencatatan frame yang sama dua kali
        self._last_logged_frame = -1

        # Status dan kontrol thread logging
        self.logging_active = False           # True jika sedang merekam
        self.thread         = None            # referensi ke thread logging
        self.stop_event     = threading.Event()  # sinyal untuk menghentikan thread


    def start(self, detector):
        """
        Memulai proses perekaman data di thread latar belakang.
        Jika perekaman sudah aktif, fungsi ini tidak melakukan apa-apa.

        Parameter:
            detector : objek FishDetector yang datanya akan direkam
        """

        if self.logging_active:
            return

        self.logging_active     = True
        self.stop_event.clear()           # reset sinyal berhenti
        self._last_logged_frame = -1      # reset penanda frame terakhir

        # Buat dan jalankan thread yang memanggil run_logging()
        # daemon=True agar thread ikut berhenti jika program ditutup paksa
        self.thread = threading.Thread(
            target=self.run_logging,
            args=(detector,),
            daemon=True
        )

        self.thread.start()


    def stop_and_save(self):
        """
        Menghentikan perekaman dan langsung menyimpan data ke file CSV.
        Jika perekaman tidak sedang aktif, tidak melakukan apa-apa.

        Return:
            path lengkap file CSV yang baru disimpan, atau None jika
            perekaman memang tidak sedang berjalan
        """

        if not self.logging_active:
            return None

        # Kirim sinyal berhenti ke thread logging
        self.logging_active = False
        self.stop_event.set()

        # Tunggu thread benar-benar selesai (maksimal 1 detik)
        if self.thread is not None:
            self.thread.join(timeout=1.0)

        # Tulis semua data yang sudah terkumpul ke file CSV
        return self.save_csv()


    def run_logging(self, detector):
        """
        Loop utama perekaman yang berjalan di thread latar belakang.
        Berjalan terus selama logging_active = True.

        Setiap 1 detik, catat satu baris snapshot berisi:
            timestamp, count_total, fps_loop, fps_yolo

        Tidak tergantung pada frame baru atau perubahan count, jadi tetap
        mencatat baris meski tidak ada objek terdeteksi.

        Parameter:
            detector : objek FishDetector sumber data (count_total, fps_loop, fps_yolo)
        """

        while self.logging_active and not self.stop_event.is_set():

            # Catat satu baris snapshot kondisi saat ini
            timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.log_rows.append([
                timestamp_now,           # tanggal + jam saat snapshot dicatat
                detector.count_total,    # total ikan yang sudah dihitung
                detector.fps_loop,       # FPS pembacaan kamera saat ini
                detector.fps_yolo        # FPS inferensi YOLO saat ini
            ])

            # Tunggu 1 detik sebelum mencatat snapshot berikutnya
            # Memakai stop_event.wait() agar bisa langsung berhenti
            # tanpa menunggu penuh 1 detik saat logging dihentikan
            self.stop_event.wait(timeout=1.0)


    def save_csv(self):
        """
        Menulis semua data yang tersimpan di log_rows ke sebuah file TXT baru.
        Nama file diberi timestamp otomatis agar tidak saling menimpa.
        Setelah disimpan, log_rows dikosongkan kembali.

        Return:
            path lengkap file TXT yang baru dibuat (string)
        """

        # Buat folder log jika belum ada (exist_ok=True agar tidak error
        # jika foldernya sudah ada)
        os.makedirs(self.log_folder, exist_ok=True)

        # Buat nama file berdasarkan waktu saat ini, contoh:
        # deteksi_2026-06-16_14-30-00.txt
        timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename      = os.path.join(
            self.log_folder,
            f"deteksi_{timestamp_now}.txt"
        )

        # Tulis header dan semua baris data ke file
        # newline="" diperlukan agar tidak ada baris kosong di antara data
        # pada sistem Windows
        with open(filename, "w", newline="") as f:

            # Tulis baris header kolom
            f.write("timestamp;count;fps_loop;fps_yolo\n")

            # Tulis setiap baris data, nilai dipisahkan tanda titik koma
            for row in self.log_rows:
                f.write(";".join(map(str, row)) + "\n")

        # Kosongkan buffer agar siap untuk sesi perekaman berikutnya
        self.log_rows = []

        return filename