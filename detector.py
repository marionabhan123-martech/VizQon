import cv2
import time
import threading
import numpy as np
from ultralytics import YOLO
from sort import Sort
from counter import process_tracking, draw_overlay


class FishDetector:
    """
    Kelas utama yang mengelola seluruh proses deteksi ikan.
    Tugasnya meliputi:
      - Membaca frame dari kamera/video
      - Menjalankan model YOLO untuk mendeteksi ikan
      - Meneruskan hasil deteksi ke tracker SORT
      - Menghitung ikan yang melintas garis
    Semua proses berjalan di thread terpisah agar GUI tetap responsif.
    """

    def __init__(self, config):
        """
        Inisialisasi semua komponen yang dibutuhkan detektor.
        Dipanggil satu kali saat program pertama kali dijalankan.

        Parameter:
            config: modul config.py yang berisi semua pengaturan
        """

        self.config = config

        # --------------------------------------------------
        # Muat model YOLO dari file .pt yang sudah dilatih
        # --------------------------------------------------
        self.model = YOLO(config.MODEL_PATH)

        # --------------------------------------------------
        # Pengaturan sumber video dan resolusi kamera
        # --------------------------------------------------
        self.camera_index = config.CAMERA_INDEX
        self.cap_width    = config.CAP_WIDTH
        self.cap_height   = config.CAP_HEIGHT

        # --------------------------------------------------
        # Pengaturan inferensi YOLO
        # --------------------------------------------------
        self.conf_thresh = config.CONF_THRESH   # batas minimum confidence
        self.img_size    = config.IMG_SIZE       # ukuran input gambar ke YOLO
        self.skip_n      = config.SKIP_N         # proses YOLO setiap N frame

        # --------------------------------------------------
        # Inisialisasi tracker SORT
        # SORT menghubungkan deteksi antar frame menjadi track
        # berkesinambungan dan memberi setiap objek sebuah ID unik
        # --------------------------------------------------
        self.tracker = Sort(
            max_age=config.SORT_MAX_AGE,
            min_hits=config.SORT_MIN_HITS,
            iou_threshold=config.SORT_IOU_THRESHOLD
        )

        # --------------------------------------------------
        # Pengaturan garis penghitung virtual
        # --------------------------------------------------
        self.line_pos    = config.LINE_POSITION  # posisi garis (0.0 - 1.0)
        self.line_offset = config.LINE_OFFSET    # toleransi piksel crossing

        # --------------------------------------------------
        # Warna bounding box dan garis (format BGR OpenCV)
        # --------------------------------------------------
        self.color_before = config.COLOR_BEFORE  # merah  : belum melewati garis
        self.color_after  = config.COLOR_AFTER   # hijau  : sudah melewati garis
        self.color_line   = config.COLOR_LINE    # hijau  : warna garis penghitung

        # --------------------------------------------------
        # Penyimpanan hasil tracking terbaru
        # Setiap elemen: [x1, y1, x2, y2, track_id, conf]
        # --------------------------------------------------
        self.cached_tracks = []

        # --------------------------------------------------
        # Status penghitungan ikan
        # track_history : menyimpan posisi X terakhir tiap ID
        # counted_ids   : set ID ikan yang sudah dihitung
        # --------------------------------------------------
        self.track_history = {}
        self.counted_ids   = set()

        # --------------------------------------------------
        # Frame BGR terbaru dari kamera (dibaca oleh GUI)
        # Dilindungi lock agar aman diakses dari dua thread
        # --------------------------------------------------
        self.latest_frame_bgr  = None
        self.latest_frame_lock = threading.Lock()

        # --------------------------------------------------
        # Penghitung total ikan yang melintas
        # --------------------------------------------------
        self.count_total = 0

        # --------------------------------------------------
        # Nomor frame saat ini (digunakan oleh logger)
        # --------------------------------------------------
        self.frame_id = 0

        # --------------------------------------------------
        # Nilai FPS yang ditampilkan di GUI
        # fps_loop : kecepatan baca frame dari kamera
        # fps_yolo : kecepatan inferensi model YOLO
        # --------------------------------------------------
        self.fps_loop          = 0
        self.fps_yolo          = 0
        self._loop_prev_time   = time.time()

        # --------------------------------------------------
        # Kontrol thread deteksi
        # --------------------------------------------------
        self.stop_event = threading.Event()  # sinyal untuk menghentikan thread
        self.det_thread = None               # referensi ke thread yang berjalan
        self.running    = False              # status apakah deteksi sedang aktif


    def start(self):
        """
        Memulai proses deteksi di thread latar belakang.
        Jika deteksi sudah berjalan, fungsi ini tidak melakukan apa-apa.
        """

        if self.running:
            return

        self.running = True
        self.stop_event.clear()

        # Buat dan jalankan thread baru yang menjalankan run_detection()
        # daemon=True berarti thread otomatis berhenti jika program ditutup
        self.det_thread = threading.Thread(
            target=self.run_detection,
            daemon=True
        )

        self.det_thread.start()


    def stop(self):
        """
        Menghentikan proses deteksi dan menunggu thread selesai.
        FPS direset ke 0 setelah thread berhenti.
        """

        if not self.running:
            return

        self.running = False
        self.stop_event.set()  # kirim sinyal berhenti ke thread

        # Tunggu thread benar-benar selesai (maksimal 2 detik)
        if self.det_thread is not None:
            self.det_thread.join(timeout=2.0)

        self.det_thread = None
        self.fps_loop   = 0
        self.fps_yolo   = 0


    def process_tracking(self, frame, tracks, conf_map):
        """
        Delegasi ke fungsi process_tracking() di counter.py.
        Memproses hasil tracker SORT untuk mendeteksi ikan yang melintas garis
        dan memperbarui cached_tracks.

        Parameter:
            frame    : frame video saat ini (numpy array BGR)
            tracks   : array hasil tracker SORT [x1,y1,x2,y2,track_id]
            conf_map : dict pemetaan track_id -> nilai confidence
        """
        process_tracking(self, frame, tracks, conf_map)


    def draw_overlay(self, frame):
        """
        Delegasi ke fungsi draw_overlay() di counter.py.
        Menggambar bounding box, centroid, label ID, dan garis penghitung
        di atas frame video.

        Parameter:
            frame : frame video yang akan digambar (numpy array BGR)

        Return:
            frame yang sudah diberi overlay gambar
        """
        return draw_overlay(self, frame)


    def run_detection(self):
        """
        Loop utama deteksi yang berjalan di thread latar belakang.
        Urutan kerjanya setiap iterasi:
          1. Baca frame dari kamera/video
          2. Hitung FPS loop
          3. Simpan frame terbaru untuk ditampilkan GUI
          4. Setiap SKIP_N frame: jalankan YOLO, update SORT, hitung crossing
        Loop berhenti ketika stop_event diset oleh stop().
        """

        # Buka sumber video (file atau kamera)
        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.cap_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cap_height)

        self.frame_id = 0

        while not self.stop_event.is_set():

            ret, frame = cap.read()

            # Jika frame tidak terbaca (misal video habis), tunggu sebentar
            if not ret:
                time.sleep(0.01)
                continue

            # -----------------------------------------------
            # Hitung FPS loop (kecepatan baca frame kamera)
            # -----------------------------------------------
            now = time.time()
            dt  = now - self._loop_prev_time

            if dt > 0:
                self.fps_loop = int(1.0 / dt)

            self._loop_prev_time = now

            # -----------------------------------------------
            # Simpan salinan frame terbaru dengan thread-safe
            # agar GUI bisa mengambilnya kapan saja
            # -----------------------------------------------
            with self.latest_frame_lock:
                self.latest_frame_bgr = frame.copy()

            self.frame_id += 1

            # -----------------------------------------------
            # Lewati YOLO jika belum waktunya (sesuai SKIP_N)
            # -----------------------------------------------
            run_yolo = (self.frame_id % self.skip_n == 0)

            if not run_yolo:
                continue

            # -----------------------------------------------
            # LANGKAH 1: Jalankan YOLO dan ukur waktunya
            # -----------------------------------------------
            yolo_start = time.time()

            results = self.model(
                frame,
                conf=self.conf_thresh,
                imgsz=self.img_size,
                verbose=False        # matikan log output ke terminal
            )

            yolo_dt = time.time() - yolo_start

            if yolo_dt > 0:
                self.fps_yolo = int(1.0 / yolo_dt)

            # -----------------------------------------------
            # LANGKAH 2: Konversi output YOLO ke format SORT
            # SORT membutuhkan array [x1, y1, x2, y2, conf]
            # -----------------------------------------------
            detections = []

            for result in results:

                boxes = result.boxes.xyxy.cpu().numpy()   # koordinat bounding box
                confs = result.boxes.conf.cpu().numpy()   # nilai confidence tiap box

                for box, conf in zip(boxes, confs):
                    x1, y1, x2, y2 = map(int, box)
                    detections.append([x1, y1, x2, y2, conf])

            # Jika tidak ada deteksi, beri array kosong ke SORT
            if len(detections) > 0:
                det_array = np.array(detections)
            else:
                det_array = np.empty((0, 5))

            # -----------------------------------------------
            # LANGKAH 3: Update tracker SORT
            # SORT mengembalikan track aktif: [x1,y1,x2,y2,track_id]
            # -----------------------------------------------
            tracks = self.tracker.update(det_array)

            # -----------------------------------------------
            # LANGKAH 4: Buat peta track_id -> confidence
            # Caranya: cocokkan setiap track dengan deteksi
            # yang posisi centroid-nya paling dekat
            # -----------------------------------------------
            conf_map = {}

            for det in detections:

                dx1, dy1, dx2, dy2, dconf = det
                dcx = (dx1 + dx2) / 2   # centroid X deteksi
                dcy = (dy1 + dy2) / 2   # centroid Y deteksi

                for track in tracks:

                    tx1, ty1, tx2, ty2, tid = track.astype(int)
                    tcx = (tx1 + tx2) / 2   # centroid X track
                    tcy = (ty1 + ty2) / 2   # centroid Y track

                    # Jarak Manhattan antara centroid deteksi dan track
                    dist = abs(dcx - tcx) + abs(dcy - tcy)

                    # Simpan conf dari deteksi yang paling dekat dengan track ini
                    if tid not in conf_map or dist < conf_map.get(f"_dist_{tid}", 9999):
                        conf_map[tid]              = dconf
                        conf_map[f"_dist_{tid}"]   = dist

            # Hapus key sementara _dist_ yang tidak perlu diteruskan
            conf_map = {
                k: v for k, v in conf_map.items()
                if not str(k).startswith("_dist_")
            }

            # -----------------------------------------------
            # LANGKAH 5: Proses crossing garis dan update cache
            # -----------------------------------------------
            self.process_tracking(frame, tracks, conf_map)

        # Lepaskan resource kamera/video setelah loop selesai
        cap.release()


    def get_latest_frame(self):
        """
        Mengambil salinan frame terbaru secara thread-safe untuk ditampilkan GUI.

        Return:
            frame BGR terbaru (numpy array), atau None jika belum ada frame
        """

        with self.latest_frame_lock:

            if self.latest_frame_bgr is None:
                return None

            return self.latest_frame_bgr.copy()


    def reset_count(self):
        """
        Mereset semua data penghitungan ke kondisi awal.
        Dipanggil ketika tombol RESET COUNT ditekan di GUI.
        """

        self.count_total   = 0       # total hitungan kembali ke nol
        self.counted_ids.clear()     # hapus semua ID yang sudah dihitung
        self.track_history.clear()   # hapus riwayat posisi semua track
        self.cached_tracks = []      # kosongkan cache track untuk overlay