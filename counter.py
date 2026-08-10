import cv2


def process_tracking(detector, frame, tracks, conf_map):
    """
    Memproses hasil tracker SORT untuk mendeteksi ikan yang melintas garis
    dan memperbarui daftar track aktif (cached_tracks).

    Logika penghitungan:
      Ikan dihitung satu kali jika:
        - Posisi X sebelumnya berada di KANAN garis (previous_x > line_x + offset)
        - Posisi X sekarang berada di KIRI  garis (x1 <= line_x - offset)
        - ID ikan tersebut belum pernah dihitung sebelumnya

    Parameter:
        detector  : objek FishDetector (menyimpan status dan pengaturan)
        frame     : frame video saat ini (numpy array BGR), digunakan untuk
                    mengetahui ukuran layar dan menghitung posisi garis
        tracks    : array hasil SORT berisi [x1, y1, x2, y2, track_id]
                    untuk setiap objek yang sedang dilacak
        conf_map  : dict { track_id -> confidence } dari deteksi YOLO
    """

    # Ambil lebar frame untuk menghitung posisi garis dalam piksel
    h, w, _ = frame.shape
    line_x  = int(w * detector.line_pos)   # posisi X garis (piksel)
    offset  = detector.line_offset         # toleransi jarak crossing

    # Daftar track baru yang akan menggantikan cached_tracks lama
    new_cached = []

    for track in tracks:

        # Pisahkan data track menjadi koordinat box dan ID objek
        x1, y1, x2, y2, track_id = track.astype(int)

        # Hitung pusat horizontal bounding box (centroid X)
        center_x = int((x1 + x2) / 2)

        # Ambil nilai confidence dari peta, default 0.0 jika tidak ada
        conf = conf_map.get(track_id, 0.0)

        # -------------------------------------------------------
        # Catat posisi X pertama kali objek ini terdeteksi
        # -------------------------------------------------------
        if track_id not in detector.track_history:
            detector.track_history[track_id] = center_x

        # Simpan posisi X frame sebelumnya, lalu perbarui dengan posisi kini
        previous_x = detector.track_history[track_id]
        detector.track_history[track_id] = center_x

        # -------------------------------------------------------
        # Cek apakah ikan baru saja melintas garis dari kanan ke kiri
        # Syarat:
        #   1. Frame sebelumnya: objek ada di KANAN garis
        #   2. Frame sekarang : sisi kiri box sudah di KIRI garis
        #   3. Objek ini belum pernah dihitung
        # -------------------------------------------------------
        crossed = (
            previous_x > line_x + offset    # sebelumnya di kanan
            and x1 <= line_x - offset        # sekarang sudah di kiri
            and track_id not in detector.counted_ids
        )

        if crossed:
            detector.count_total += 1              # tambah hitungan total
            detector.counted_ids.add(track_id)     # tandai ID ini sudah dihitung

        # Simpan data track lengkap untuk digunakan oleh draw_overlay
        new_cached.append([x1, y1, x2, y2, track_id, conf])

    # Ganti cache lama dengan hasil tracking frame ini
    detector.cached_tracks = new_cached


def draw_overlay(detector, frame):
    """
    Menggambar semua elemen visual di atas frame video:
      - Garis penghitung vertikal
      - Bounding box tiap ikan (merah = belum lewat, hijau = sudah lewat)
      - Titik centroid di tengah bounding box
      - Label berisi ID track dan nilai confidence

    Parameter:
        detector : objek FishDetector (menyimpan cached_tracks, warna, dll.)
        frame    : frame video yang akan diberi gambar (numpy array BGR)

    Return:
        frame yang sudah diberi semua overlay visual
    """

    # Hitung posisi garis penghitung dalam piksel
    h, w, _ = frame.shape
    line_x  = int(w * detector.line_pos)

    # -------------------------------------------------------
    # Gambar garis penghitung vertikal
    # Titik atas: (line_x, 0) | Titik bawah: (line_x, h)
    # -------------------------------------------------------
    cv2.line(
        frame,
        (line_x, 0),          # titik atas garis
        (line_x, h),          # titik bawah garis
        detector.color_line,  # warna garis (dari config)
        1                     # ketebalan garis (piksel)
    )

    # -------------------------------------------------------
    # Gambar bounding box dan label untuk setiap track aktif
    # -------------------------------------------------------
    for entry in detector.cached_tracks:

        x1, y1, x2, y2, track_id, conf = entry

        # Tentukan warna: hijau jika sudah dihitung, merah jika belum
        if track_id in detector.counted_ids:
            color = detector.color_after    # hijau
        else:
            color = detector.color_before   # merah

        # Hitung koordinat pusat bounding box (centroid)
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)

        # Gambar kotak bounding box di sekitar ikan
        """cv2.rectangle(
            frame,
            (x1, y1),   # sudut kiri atas
            (x2, y2),   # sudut kanan bawah
            color,
            1            # ketebalan garis kotak
        )

        # Gambar titik kecil putih di pusat bounding box (centroid)
        cv2.circle(
            frame,
            (center_x, center_y),
            2,              # radius titik (piksel)
            (255, 255, 255),# warna putih (BGR)
            -1              # -1 = lingkaran terisi penuh
        )

        # Tulis label "ID:X  0.xx" di atas bounding box
        label = f"ID:{track_id}  {conf:.2f}"

        cv2.putText(
            frame,
            label,
            (x1, y1 - 10),          # posisi teks: sedikit di atas kotak
            cv2.FONT_HERSHEY_SIMPLEX,# jenis font
            0.5,                     # ukuran font
            color,                   # warna teks (sama dengan warna kotak)
            1                        # ketebalan teks
        )"""

    return frame