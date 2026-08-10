import cv2
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageEnhance


class FishCounterGUI:
    """
    Kelas yang mengelola seluruh tampilan antarmuka grafis (GUI) program.

    Tanggung jawabnya meliputi:
      - Menampilkan video deteksi secara real-time di layar
      - Menampilkan nilai COUNT, FPS LOOP, dan FPS YOLO yang selalu diperbarui
      - Menyediakan tombol-tombol kontrol: START/STOP CAMERA, RECORD DATA,
        RESET COUNT, dan QUIT
      - Menjalankan animasi fade-out saat kamera dihentikan
    """

    def __init__(self, config, detector, logger):
        """
        Inisialisasi jendela utama GUI dan semua komponennya.
        Dipanggil satu kali saat program pertama dijalankan.

        Parameter:
            config   : modul config.py berisi pengaturan GUI (update interval, logo, dll.)
            detector : objek FishDetector sebagai sumber frame dan data deteksi
            logger   : objek FishLogger untuk mengontrol perekaman data
        """

        self.config   = config
        self.detector = detector
        self.logger   = logger

        # Interval pembaruan tampilan dalam milidetik (dari config)
        self.gui_update_ms = config.GUI_UPDATE_MS

        # Path file gambar logo (digunakan di setup_gui)
        self.logo_path = config.LOGO_PATH

        # --------------------------------------------------
        # Buat jendela utama tkinter
        # --------------------------------------------------
        self.root = tk.Tk()
        self.root.configure(bg="white")
        self.root.title("Automatic Fish Counter 1.0")
        self.root.state("normal")          # buka dalam kondisi layar penuh
        self.root.resizable(True, True)    # jendela bisa diubah ukurannya

        # Frame PIL terakhir yang ditampilkan (digunakan untuk efek fade-out)
        self.last_frame_pil = None

        # Menyimpan referensi objek ImageTk logo agar tidak di-garbage collect
        self.logo_tk = None

        # Bangun semua widget (label, tombol, frame video, dll.)
        self.setup_gui()

        # Jadwalkan pembaruan GUI pertama setelah gui_update_ms milidetik
        self.root.after(self.gui_update_ms, self.update_gui_loop)

        # Tangkap event tombol X (tutup jendela) agar quit_app() dipanggil
        # sehingga thread deteksi dan logger ikut dihentikan dengan benar
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)


    def setup_gui(self):
        """
        Membangun dan menempatkan semua widget di jendela utama.
        Dipanggil sekali oleh __init__. Terdiri dari empat bagian:
          1. Judul program di bagian atas
          2. Area tampilan video di kiri
          3. Panel kontrol (tombol + data) di kanan
          4. Label identitas di sudut kanan bawah
        """

        # =====================================================
        # BAGIAN 1: JUDUL PROGRAM (atas tengah)
        # =====================================================
        tk.Label(
            self.root,
            text="Automatic Fish Counter 1.0",
            bg="white",
            font=("Arial", 30, "bold")
        ).place(relx=0.23, rely=0.01)


        # =====================================================
        # BAGIAN 2: AREA TAMPILAN VIDEO (kiri, 60% lebar layar)
        # =====================================================

        # Frame hitam sebagai bingkai area video
        frame_left = tk.Frame(
            self.root,
            bg="black",
            bd=3,
            relief="ridge"    # efek tepi seperti bingkai timbul
        )
        frame_left.place(
            relx=0.02,
            rely=0.10,
            relwidth=0.60,
            relheight=0.86
        )

        # Label di dalam frame_left yang akan menampilkan setiap frame video
        self.video_label = tk.Label(frame_left, bg="black")
        self.video_label.place(relwidth=1, relheight=1)


        # =====================================================
        # BAGIAN 3: PANEL KONTROL (kanan, 33% lebar layar)
        # =====================================================

        # Frame putih sebagai wadah semua kontrol
        panel = tk.Frame(
            self.root,
            bg="white",
            bd=3,
            relief="ridge"
        )
        panel.place(
            relx=0.64,
            rely=0.10,
            relwidth=0.33,
            relheight=0.86
        )

        # Judul panel
        tk.Label(
            panel,
            text="CONTROL PANEL",
            font=("Arial", 22, "bold"),
            bg="white"
        ).place(relx=0.115, rely=0.01)

        # --------------------------------------------------
        # Logo institusi (opsional, dilewati jika file tidak ada)
        # --------------------------------------------------
        if self.logo_path:
            try:
                logo_img     = Image.open(self.logo_path).convert("RGBA")
                logo_img     = logo_img.resize((70, 70))
                self.logo_tk = ImageTk.PhotoImage(logo_img)

                tk.Label(
                    self.root,
                    image=self.logo_tk,
                    bg="white"
                ).place(relx=0.77, rely=0.62)

            except:
                # Jika file logo tidak ditemukan, lewati tanpa error
                pass

        # --------------------------------------------------
        # Label identitas peneliti dan institusi (kanan bawah)
        # --------------------------------------------------
        tk.Label(
            self.root,
            text="Universitas Jenderal Soedirman",
            bg="white",
            font=("Arial", 11, "bold")
        ).place(relx=0.695, rely=0.87)

        tk.Label(
            self.root,
            text="Fakultas Perikanan dan Ilmu Kelautan",
            bg="white",
            font=("Arial", 11, "bold")
        ).place(relx=0.675, rely=0.84)

        tk.Label(
            self.root,
            text="2026",
            bg="white",
            font=("Arial", 11, "bold")
        ).place(relx=0.79, rely=0.9)

        tk.Label(
            self.root,
            text="Mario Nabhan",
            bg="white",
            font=("Arial", 11, "bold")
        ).place(relx=0.76, rely=0.77)

        tk.Label(
            self.root,
            text="L1C022078",
            bg="white",
            font=("Arial", 11, "bold")
        ).place(relx=0.77, rely=0.80)

        # --------------------------------------------------
        # Label data real-time (COUNT, FPS LOOP, FPS YOLO)
        # Nilainya diperbarui setiap gui_update_ms oleh update_gui_loop()
        # --------------------------------------------------
        self.count_label     = tk.Label(panel, text="0", font=("Arial", 16, "bold"), bg="white")
        self.fps_label       = tk.Label(panel, text="0", font=("Arial", 16, "bold"), bg="white")
        self.fps_yolo_label  = tk.Label(panel, text="0", font=("Arial", 16, "bold"), bg="white")

        # Teks keterangan (kiri) dan nilai dinamis (kanan)
        tk.Label(panel, text="COUNT :",    font=("Arial", 16), bg="white").place(relx=0.15, rely=0.09)
        tk.Label(panel, text="FPS LOOP :", font=("Arial", 16), bg="white").place(relx=0.15, rely=0.14)
        tk.Label(panel, text="FPS YOLO :", font=("Arial", 16), bg="white").place(relx=0.15, rely=0.19)

        self.count_label.place(relx=0.75,    rely=0.09)
        self.fps_label.place(relx=0.75,      rely=0.14)
        self.fps_yolo_label.place(relx=0.75, rely=0.19)

        # =====================================================
        # BAGIAN 4: TOMBOL-TOMBOL KONTROL
        # Helper lokal make_button() menghindari pengulangan kode
        # =====================================================

        def make_button(txt, color, rely, cmd):
            """
            Membuat satu tombol dan langsung menempatkannya di panel.

            Parameter:
                txt   : teks yang tampil di tombol
                color : warna latar tombol (hex string, misal "#22DD77")
                rely  : posisi vertikal relatif di dalam panel (0.0 - 1.0)
                cmd   : fungsi yang dipanggil saat tombol ditekan
            Return:
                objek Button yang sudah ditempatkan
            """
            btn = tk.Button(
                panel,
                text=txt,
                font=("Arial", 14, "bold"),
                bg=color,
                fg="black",
                command=cmd
            )
            btn.place(
                relx=0.15,
                rely=rely,
                relwidth=0.70,
                relheight=0.07
            )
            return btn

        # Tombol RESET: mereset hitungan ikan ke nol
        make_button("RESET COUNT", "#F7E96B", 0.27, self.reset_count)

        # Tombol START/STOP CAMERA: disimpan agar teksnya bisa diubah nanti
        self.camera_button = make_button(
            "START CAMERA", "#22DD77", 0.35, self.toggle_camera
        )

        # Tombol RECORD DATA: dinonaktifkan sampai kamera dinyalakan
        self.save_button = make_button(
            "RECORD DATA", "#808080", 0.43, self.toggle_logging
        )
        self.save_button.config(state="disabled")

        # Tombol QUIT: menutup program dengan aman
        make_button("QUIT", "#FF4444", 0.51, self.quit_app)


    def fade_out_frame(self, steps=18, delay=30):
        """
        Menampilkan animasi fade-out (frame perlahan menghitam) saat
        kamera dihentikan, sehingga transisi tampak halus.

        Cara kerja:
          Fungsi rekursif fade() dipanggil berulang via widget.after(),
          setiap pemanggilan mengurangi kecerahan frame satu langkah
          hingga layar menjadi hitam sepenuhnya.

        Parameter:
            steps : jumlah langkah animasi (lebih banyak = lebih halus)
            delay : jeda antar langkah dalam milidetik
        """

        # Jika tidak ada frame yang pernah ditampilkan, tidak perlu fade
        if self.last_frame_pil is None:
            return

        def fade(step):
            """Satu langkah animasi fade; memanggil dirinya sendiri secara rekursif."""

            if step >= steps:
                # Animasi selesai: tampilkan gambar hitam polos
                empty    = Image.new("RGB", self.last_frame_pil.size, (0, 0, 0))
                empty_tk = ImageTk.PhotoImage(empty)
                self.video_label.configure(image=empty_tk)
                self.video_label.image = empty_tk
                return

            # Hitung faktor kecerahan: 1.0 (terang) turun ke 0.0 (gelap)
            factor   = 1.0 - (step / steps)
            enhancer = ImageEnhance.Brightness(self.last_frame_pil)
            faded    = enhancer.enhance(factor)

            faded_tk = ImageTk.PhotoImage(faded)
            self.video_label.configure(image=faded_tk)
            self.video_label.image = faded_tk  # simpan referensi agar tidak hilang

            # Jadwalkan langkah berikutnya setelah 'delay' milidetik
            self.video_label.after(delay, lambda: fade(step + 1))

        fade(0)  # mulai animasi dari langkah pertama


    def update_gui_loop(self):
        """
        Loop pembaruan GUI yang dipanggil secara berkala oleh tkinter.
        Setiap pemanggilan melakukan dua hal:
          1. Jika deteksi sedang berjalan: ambil frame terbaru, gambar
             overlay, lalu tampilkan di video_label
          2. Perbarui angka COUNT, FPS LOOP, dan FPS YOLO di panel kanan

        Fungsi ini menjadwalkan dirinya sendiri kembali di akhir,
        sehingga terus berjalan selama GUI aktif.
        """

        if self.detector.running:

            frame = self.detector.get_latest_frame()

            if frame is not None:

                # Gambar bounding box, garis, dan label di atas frame
                frame = self.detector.draw_overlay(frame)

                # Konversi dari BGR (OpenCV) ke RGB (PIL/tkinter)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Sesuaikan ukuran frame dengan ukuran widget video saat ini
                # min 300x200 agar tidak error saat jendela baru dibuka
                w_gui = max(300, self.video_label.winfo_width())
                h_gui = max(200, self.video_label.winfo_height())

                frame_resized = cv2.resize(
                    frame_rgb,
                    (w_gui, h_gui),
                    interpolation=cv2.INTER_AREA   # kualitas resize yang baik
                )

                # Konversi numpy array ke format yang bisa ditampilkan tkinter
                pil_img = Image.fromarray(frame_resized)

                # Simpan salinan frame PIL untuk keperluan animasi fade-out
                self.last_frame_pil = pil_img.copy()

                # Tampilkan gambar di label video
                img = ImageTk.PhotoImage(pil_img)
                self.video_label.configure(image=img)
                self.video_label.image = img   # simpan referensi agar tidak hilang

        # Perbarui label COUNT, FPS LOOP, FPS YOLO dengan nilai terkini
        self.count_label.config(text=str(self.detector.count_total))
        self.fps_label.config(text=str(self.detector.fps_loop))
        self.fps_yolo_label.config(text=str(self.detector.fps_yolo))

        # Jadwalkan pemanggilan berikutnya setelah gui_update_ms milidetik
        self.root.after(self.gui_update_ms, self.update_gui_loop)


    def toggle_camera(self):
        """
        Tombol START/STOP CAMERA: mengaktifkan atau menghentikan kamera.

        Jika kamera belum berjalan:
          - Mulai deteksi
          - Ubah tombol menjadi "STOP CAMERA" (biru)
          - Aktifkan tombol RECORD DATA

        Jika kamera sedang berjalan:
          - Hentikan logger (simpan data jika sedang merekam)
          - Hentikan deteksi
          - Nonaktifkan tombol RECORD DATA
          - Jalankan animasi fade-out pada video
          - Kembalikan tombol ke "START CAMERA" (hijau)
        """

        if not self.detector.running:

            # --- Nyalakan kamera ---
            self.detector.start()
            self.camera_button.config(text="STOP CAMERA", bg="#66BBFF")
            self.save_button.config(state="normal")

        else:

            # --- Matikan kamera ---

            # Tampilkan status "sedang berhenti" sementara
            self.camera_button.config(text="STOPPING...", bg="#FFCC66")

            # Hentikan logger terlebih dahulu (simpan CSV jika aktif)
            self.logger.stop_and_save()

            # Hentikan thread deteksi
            self.detector.stop()

            # Nonaktifkan tombol rekaman dan kembalikan ke kondisi awal
            self.save_button.config(
                state="disabled",
                text="RECORD DATA",
                bg="#808080"
            )

            # Jalankan animasi layar menghitam perlahan
            self.fade_out_frame()

            # Kembalikan tombol kamera ke kondisi awal
            self.camera_button.config(text="START CAMERA", bg="#22DD77")


    def toggle_logging(self):
        """
        Tombol RECORD DATA: memulai atau menghentikan perekaman ke CSV.

        Jika perekaman belum aktif:
          - Mulai logging
          - Ubah teks tombol menjadi "STOP RECORD & SAVE DATA"

        Jika perekaman sudah aktif:
          - Hentikan logging dan simpan file CSV
          - Kembalikan teks tombol ke "RECORD DATA"
          - Tampilkan dialog notifikasi berisi path file yang disimpan

        Catatan: tidak melakukan apa-apa jika kamera tidak sedang berjalan.
        """

        # Abaikan jika kamera belum dinyalakan
        if not self.detector.running:
            return

        if not self.logger.logging_active:

            # --- Mulai merekam ---
            self.logger.start(self.detector)
            self.save_button.config(text="STOP RECORD & SAVE DATA", bg="#808080")

        else:

            # --- Hentikan dan simpan ---
            filename = self.logger.stop_and_save()
            self.save_button.config(text="RECORD DATA", bg="#808080")

            # Tampilkan notifikasi lokasi file CSV yang tersimpan
            if filename:
                messagebox.showinfo(
                    "Saved",
                    f"Data tersimpan:\n{filename}"
                )


    def reset_count(self):
        """
        Tombol RESET COUNT: mereset semua data penghitungan ke nol.
        Mendelegasikan ke detector.reset_count() yang mengosongkan
        counted_ids, track_history, cached_tracks, dan count_total.
        """
        self.detector.reset_count()


    def quit_app(self):
        """
        Menutup program secara aman.
        Dipanggil oleh tombol QUIT maupun tombol X di pojok jendela.

        Urutan penghentian:
          1. Hentikan logger (simpan data jika sedang merekam)
          2. Hentikan thread deteksi
          3. Tutup jendela tkinter

        Masing-masing dibungkus try-except agar satu kegagalan tidak
        menghalangi langkah berikutnya.
        """

        try:
            self.logger.stop_and_save()
        except:
            pass

        try:
            self.detector.stop()
        except:
            pass

        self.root.destroy()


    def run(self):
        """
        Menjalankan event loop tkinter.
        Program akan berhenti di sini hingga jendela ditutup.
        Harus dipanggil terakhir dari main.py setelah semua inisialisasi selesai.
        """
        self.root.mainloop()