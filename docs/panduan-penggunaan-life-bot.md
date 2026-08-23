# Panduan Penggunaan Life Bot

Life adalah bot pendamping untuk mengatur rutinitas, pengingat, makanan, berat badan, olahraga, dan daftar belanja. Gunakan **Telegram bot** untuk membuka aplikasi serta menerima pengingat; gunakan **Life Mini App** untuk mengatur dan mencatat semuanya.

> Singkatnya: bot = pintu masuk + notifikasi, Mini App = tempat mengelola aktivitas.

## Mulai dari Telegram

1. Buka percakapan dengan bot Life di Telegram.
2. Kirim `/start`.
3. Tekan **Open Life** untuk membuka Mini App.

Kamu juga bisa memakai `/app` kapan saja untuk langsung membuka Mini App.

Saat dibuka dari Telegram, Life masuk menggunakan identitas Telegram kamu. Jangan membuka tautan Mini App dari browser biasa: versi saat ini memerlukan verifikasi Telegram Mini App.

### Pakai di grup

Life tetap menyimpan data pribadi—makanan, target, berat badan, olahraga, dan grocery list—di akun Telegram masing-masing, bukan milik grup.

Untuk menjadikan grup sebagai tujuan notifikasi:

1. Tambahkan Life bot ke grup bila belum ada.
2. Kirim `/start` atau `/app` di grup agar grup tersebut dikenali oleh Life.
3. Buka Mini App, lalu masuk ke **Settings → Notifications**.
4. Pada nama grup yang muncul sebagai *not activated*, tekan **Activate**.
5. Aktifkan toggle tujuan tersebut bila perlu; pilih ikon centang untuk menjadikannya tujuan default.

Notifikasi grup dinonaktifkan secara default karena isinya dapat terlihat oleh anggota grup. Untuk menjaga privasi, pesan pengingat yang dikirim ke grup tidak menampilkan judul pengingat pribadi.

## Setup pertama kali

Sebelum membuat pengingat, buka **Settings** dari menu bawah dan isi dua hal ini.

1. **Profile details**
   - Atur zona waktu (contoh: `Asia/Jakarta`).
   - Isi nama panggilan bila diinginkan; tinggi dan jenis kelamin bersifat opsional.
2. **Calorie target**
   - Isi target kalori harian, batas minimum protein, batas maksimum protein, serta tanggal mulai berlaku.
3. **Notifications**
   - Aktifkan chat pribadi atau grup yang ingin menerima pengingat.
   - Minimal satu tujuan notifikasi harus aktif sebelum reminder atau jadwal workout dapat dibuat.

## Menu di Mini App

Navigasi utama tersedia di bawah: **Today**, **Planner**, **Grocery**, **Progress**, dan **Settings**.

### Today — cek dan catat aktivitas hari ini

Halaman **Today** adalah ringkasan harian.

- Lihat konsumsi kalori dan protein terhadap target.
- Tekan **Log meal** untuk mencatat makanan yang baru dimakan. Pilih makanan, isi jumlahnya, lalu simpan.
- Tekan **Log weight** untuk mencatat berat badan hari ini.
- Pada bagian **Next up**, selesaikan atau lewati workout hari ini dengan **Done** atau **Skip**.
- Jika belum punya workout, tekan **Create plan** untuk membuat jadwal olahraga rutin tiga kali seminggu.
- Buka **Manage food & templates** untuk menambahkan makanan kustom, menonaktifkannya, atau membuat template meal agar pencatatan berikutnya lebih cepat.

Tips: buat dulu makanan kustom beserta kalori dan protein per sajian. Setelah itu, makanan tersebut dapat dipilih saat mencatat meal atau dibuat menjadi template.

### Planner — buat dan kelola pengingat

Di **Planner**, tekan **New reminder** lalu isi:

- Judul kegiatan, misalnya “Jalan sore”.
- Jenis: Reminder, Routine, Meal, atau Workout.
- Tujuan notifikasi yang aktif.
- Zona waktu.
- Jadwal **Recurring** atau **One time**.

Untuk jadwal berulang, pilih **Every day** atau hari-hari tertentu dalam seminggu serta jamnya. Untuk jadwal sekali jalan, pilih tanggal dan jam. Catatan bersifat opsional.

Dari daftar pengingat kamu dapat:

- Menonaktifkan sementara pengingat dengan toggle.
- Mengubah detailnya lewat ikon edit.
- Menghapusnya lewat ikon silang.

### Grocery — daftar belanja

Jika belum ada daftar aktif, buat daftar **Weekly**, **Monthly**, atau pilih rentang tanggal khusus.

- Tambahkan barang dengan nama, jumlah, satuan, dan estimasi harga per satuan (opsional).
- Centang barang setelah dibeli; barang akan pindah ke bagian **Bought** dan dapat dibatalkan centangnya.
- Total estimasi ditampilkan dalam rupiah dan dihitung dari item yang ada.
- Di **Add essentials**, simpan barang yang sering dibeli sebagai *recurring item*, lalu tambahkan kembali ke daftar aktif cukup dengan satu ketukan.
- Setelah periode belanja selesai, tekan **Archive list** lalu konfirmasi. Baru setelah itu kamu dapat membuat daftar aktif berikutnya.

### Progress — lihat kebiasaan, bukan menghakimi diri

Halaman **Progress** merangkum data beberapa hari terakhir:

- Tren berat badan dari catatan weight.
- Konsistensi kalori dan protein harian dibanding target.
- Jumlah workout yang selesai, terlewati, dan direncanakan.
- Riwayat berat lebih rinci pada **View detailed history**.

### Settings — ubah preferensi dan notifikasi

Gunakan halaman ini untuk memperbarui profil, target nutrisi, dan tujuan notifikasi. Tombol avatar di kanan atas digunakan untuk keluar dari sesi Life.

## Saat pengingat datang di Telegram

Untuk pengingat pribadi, Telegram menampilkan judul dan catatan pengingat, serta tombol:

- **Done** untuk menandai kegiatan selesai.
- **Skip** untuk menandai kegiatan dilewati.
- **Open Life** untuk membuka Mini App.

Pada pengingat grocery, tersedia tombol **Open Life** agar kamu dapat langsung melihat daftar belanja.

Di grup, hanya pemilik pengingat yang boleh menggunakan **Done** atau **Skip**. Jika orang lain menekan tombolnya, Life tidak akan mengubah data pengingat.

## Troubleshooting singkat

| Masalah | Yang bisa dilakukan |
| --- | --- |
| Mini App meminta dibuka dari Telegram | Kembali ke chat bot lalu gunakan `/start` atau `/app`; jangan gunakan tautan dari browser biasa. |
| Tidak bisa membuat reminder | Buka **Settings → Notifications**, aktifkan setidaknya satu tujuan notifikasi. |
| Grup tidak muncul di Notifications | Pastikan bot sudah ada di grup, lalu kirim `/start` atau `/app` di grup dan buka ulang Mini App. |
| Jam reminder tidak sesuai | Periksa **Settings → Profile details** dan timezone pada reminder tersebut. |
| Notifikasi grup terlalu sensitif | Nonaktifkan toggle grup di **Settings → Notifications** atau ganti tujuan reminder ke chat pribadi. |
| Tombol Done/Skip di grup tidak bekerja | Hanya akun Telegram pemilik reminder yang dapat mengubah statusnya. |

## Batasan saat ini

Life menggunakan input terstruktur, bukan chat AI. Bot belum mendukung membuat reminder lewat kalimat bebas seperti “ingatkan aku besok jam tujuh”, dan belum menyediakan database makanan global, rekomendasi diet otomatis, pemesanan belanja, atau program olahraga otomatis.

