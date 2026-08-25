# Panduan Penggunaan GitLab Ops Bot

GitLab Ops Bot menghubungkan notifikasi dan aksi GitLab ke Telegram. GitLab
tetap menjadi sumber kebenaran untuk akses project, protected branch, approval,
pipeline, deployment, dan runner. Bot tidak menerima command shell dari Telegram.

Untuk konfigurasi server, webhook executor, atau recovery delivery webhook,
lihat [GitLab Ops Bot Runbook](gitlab-ops-bot-runbook.md).

## Kemampuan utama

- Menerima notifikasi push, merge request, pipeline, deployment, dan job dari
  project yang sudah didaftarkan.
- Menampilkan dan menjalankan promotion rule melalui merge request GitLab.
- Menampilkan tombol approval dan merge bila user memiliki izin yang sesuai.
- Menjalankan GitLab manual job yang sebelumnya dimapping untuk branch tertentu.
- Mengotomatisasi approval MR dan manual script untuk author GitLab yang masuk
  allowlist, dengan service account khusus per project.
- Memakai selector tombol berlabel `namespace/project` setelah project
  terdaftar; penggunaan sehari-hari tidak membutuhkan internal project ID.

## Sebelum mulai

- Lakukan koneksi GitLab dan pengiriman PAT hanya di private chat dengan bot.
- Gunakan PAT dengan akses minimum yang tetap cukup untuk project yang akan
  dikelola. Pendaftaran webhook memerlukan izin GitLab untuk mengelola project
  webhook.
- Project harus dapat diakses dari GitLab instance yang dihubungkan. URL GitLab
  harus HTTPS.
- Notifikasi dan perubahan status memerlukan webhook executor aktif pada satu
  proses aplikasi sesuai runbook.

## 1. Hubungkan identity GitLab

Di private chat, kirim:

```text
/gitlab
```

Bot meminta URL GitLab, misalnya `https://gitlab.com`, lalu meminta Personal
Access Token. Setelah token tervalidasi dan tersimpan terenkripsi, cek status:

```text
/gitlab status
```

Jika GitLab menolak token dengan HTTP 401, identity ditandai disconnected.
Jalankan `/gitlab` lagi untuk menghubungkan token baru.

## 2. Daftarkan project

Kirim perintah berikut di private chat:

```text
/gitlab projects
```

Bot menampilkan project GitLab yang dapat diakses. Balas nomor project yang
ingin didaftarkan. Saat berhasil, bot menyimpan project dan menyiapkan webhook
untuk push, merge request, pipeline, deployment, dan job event.

Lihat project aktif dengan:

```text
/projects
```

Sesudah setup, project ditampilkan sebagai `namespace/project`; Anda tidak
perlu mengingat atau mengetik project ID untuk flow operasional.

## 3. Atur notifikasi

Di private chat, mulai dengan:

```text
/gitlab subscribe
```

Pilih project dari tombol yang muncul. Bot kemudian meminta format:

```text
failures|all | branch1,release/*
```

- `failures` hanya mengirim status pipeline yang bukan `success`, `skipped`,
  atau `manual`.
- `all` mengirim semua perubahan status pipeline.
- Bagian branch filter opsional. Pisahkan beberapa pattern dengan koma.
- `*` hanya berlaku dalam satu segment branch. Contoh `release/*` cocok
  untuk `release/1.0`, tetapi bukan `release/1.0/hotfix`.

Subscription dikirim ke chat tempat perintah dijalankan. Notifikasi push, merge
request, pipeline, deployment, dan job mengikuti filter branch tersebut.

## 4. Buat promotion rule dan deploy

Promotion rule adalah label bisnis yang menyimpan arah branch, misalnya
`Staging · development → staging`. User tidak memasukkan branch bebas saat
menjalankan deploy.

Untuk membuat atau memperbarui rule, kirim:

```text
/gitlab rule
```

Pilih project, lalu kirim:

```text
Nama Rule | source-branch | target-branch
```

Contoh:

```text
Staging | development | staging
```

Untuk menjalankan promotion, gunakan di private chat atau group yang diizinkan:

```text
/deploy
```

Pilih project, lalu pilih promotion rule. Jika rule memerlukan konfirmasi, bot
menampilkan tombol konfirmasi. Bot mencari MR terbuka dengan pasangan
source/target yang sama; bila belum ada, bot membuat MR menggunakan PAT user
yang menekan aksi.

Bot tidak otomatis merge atau otomatis memicu deployment production setelah MR.
Approval, kelayakan merge, dan pipeline tetap divalidasi GitLab.

## 5. Pantau MR dan pipeline

```text
/mr
/pipeline
```

`/mr` menampilkan merge request relevan yang terbuka, sedangkan `/pipeline`
menampilkan pipeline terbaru dari project yang dapat dilihat user.

Notifikasi MR dapat memuat tombol `Approve` dan `Merge` bila user berwenang.
Tombol callback bersifat one-time, terikat ke chat, dan kedaluwarsa setelah
15 menit. Jika SHA MR berubah sebelum aksi dilakukan, bot menolak aksi sebagai
stale agar tidak meng-approve atau merge commit yang lebih baru.

## 6. Konfigurasikan manual script

Manual script hanya dapat menjalankan job GitLab yang didefinisikan di effective
CI configuration sebagai `when: manual`. Bot tidak menerima teks shell ataupun
nama command arbitrer.

Repository ini menyediakan contoh di [`.gitlab-ci.yml`](../.gitlab-ci.yml):

- Pipeline hanya menerima source `api`, sehingga push atau MR biasa tidak
  membuat pipeline.
- `run_development_script` tersedia pada branch `development`.
- `run_production_script` tersedia pada branch `production` atau `main`.
- Kedua job tetap manual dan berisi placeholder aman yang perlu diganti dengan
  script operasional sebenarnya.

Untuk membuat mapping script, kirim di private chat:

```text
/gitlab scripts
```

Pilih project, target branch, dan job manual; kemudian kirim label Telegram,
misalnya `Run Development`. Bot menyimpan nama job GitLab yang tepat dan
memberi creator izin awal untuk menjalankannya.

Untuk melihat branch sebuah project, gunakan:

```text
/gitlab branches
```

Pilih project dari selector. Daftar branch menandai branch yang protected.

## 7. Otomatisasi approval dan manual script

Automation bersifat per project dan hanya bisa diatur melalui private chat oleh
user yang memiliki permission `manage_automation`. Owner yang melakukan setup
project memperoleh permission tersebut secara default.

Siapkan lebih dulu service account GitLab terpisah. PAT-nya wajib mempunyai
scope `api` serta role yang dapat membaca project/MR/branch, memberi approval,
membuat pipeline, dan memainkan manual job. Simpan token dengan:

```text
/gitlab automation
```

Pilih project dari selector, lalu pilih `Set / Replace service PAT`. Bot
memvalidasi token dengan membaca user dan default branch project, lalu
menyimpannya terenkripsi. Token ini hanya dipakai background worker automation,
bukan untuk aksi normal yang diklik user Telegram.

Pada menu project yang sama, pilih `Add allowlist author`, lalu kirim username
GitLab dalam format `@username`.

Username di-resolve saat disimpan dan bot menyimpan numeric GitLab user ID agar
perubahan nama username tidak mengubah identitas author. Menu yang sama juga
menampilkan status service account dan allowlist; hapus author lewat tombol
`Remove @username` pada daftar tersebut.

Untuk MR `opened` dari author allowlist pada target branch non-protected, bot
memverifikasi ulang MR dan SHA melalui service account, lalu approve MR dan
menjalankan setiap mapping manual script yang cocok dengan target branch. Setiap
approval dan mapping direkam per MR/SHA sehingga webhook duplikat atau edit
metadata MR tidak menjalankan aksi dua kali. Push baru yang mengubah SHA dapat
diproses sekali lagi.

Target branch protected tidak pernah di-approve atau dijalankan otomatis. Bot
menampilkan `Confirm Approve & Run`; hanya pemilik konfigurasi yang masih punya
permission project, `manage_automation`, dan permission mapping yang dapat
menjalankannya. Konfirmasi ini tetap memakai service account.

Jika auto-action GitLab gagal, notifikasi mencantumkan status aman dan tombol
manual tetap tersedia untuk recovery. Pada auto-action sukses, tombol approval
yang sudah tidak relevan disembunyikan. Lifecycle notifikasi pipeline/job tetap
berjalan seperti biasa.

Push dari identity GitLab pemilik konfigurasi tetap mengirim notifikasi. Untuk
branch non-protected, tombol `Run` disembunyikan agar tidak memicu run manual
tambahan; branch protected tetap mempertahankan tombol dan konfirmasi kedua.

## 8. Beri izin manual script

Untuk memberikan izin mapping script kepada user yang sudah pernah berinteraksi
dengan bot, kirim di private chat:

```text
/gitlab script grant
```

Pilih project dan manual script dari tombol, lalu kirim Telegram user ID target
saat diminta. Izin ini khusus untuk mapping script tersebut; izin melihat
project tidak otomatis boleh menjalankan script.

## 9. Jalankan manual script dari notifikasi

Saat ada push ke branch yang mempunyai mapping manual script, notifikasi push
menampilkan tombol `Run <label>`. Klik tombol melakukan hal berikut:

1. Bot memeriksa izin user, chat, mapping aktif, dan SHA branch.
2. Bot membuat pipeline baru melalui GitLab API pada branch tersebut.
3. Bot mencari exact job yang telah dimapping dan memanggil play-job GitLab.
4. Pesan Telegram yang sama berubah menjadi `Running`, kemudian
   `Succeeded`, `Failed`, atau `Canceled` berdasarkan Job Hook GitLab.

Jika branch menerima push baru sebelum tombol diklik, aksi lama dianggap stale.
Gunakan tombol pada notifikasi terbaru agar script tidak berjalan pada commit
yang berbeda.

Untuk branch protected, klik pertama hanya menampilkan warning. Klik
`Confirm run` kedua diperlukan sebelum bot membuat pipeline. GitLab masih dapat
menolak aksi bila PAT user tidak memiliki izin branch/environment yang sesuai.

Jika job gagal, bot menampilkan failure reason ringkas dan tautan log job
GitLab. Raw trace job tidak disalin ke Telegram.

Notifikasi MR menuju branch yang memiliki mapping dapat menyediakan tombol
`Approve & Run <label>`. Aksi ini memverifikasi SHA MR, melakukan approval,
lalu menjalankan manual job pada HEAD terbaru **target branch**. Aksi ini tidak
merge MR dan tidak menjalankan source branch MR yang belum di-merge.

## Troubleshooting singkat

| Gejala | Tindakan |
| --- | --- |
| Project tidak muncul di selector | Pastikan project sudah didaftarkan, user punya permission bot yang sesuai, dan identity GitLab masih active. |
| Webhook berstatus `degraded` | Pastikan PAT pendaftar boleh mengelola webhook project, lalu ulangi setup project. |
| Tidak ada manual job saat setup mapping | Pastikan job ada pada effective CI config branch tersebut dan memakai `when: manual`. |
| Tombol expired atau sudah dipakai | Buat action baru dari perintah/notifikasi terbaru; callback hanya dapat dipakai sekali selama 15 menit. |
| Tombol run stale | Ada push baru pada branch; gunakan notifikasi push terbaru. |
| Automation tidak berjalan | Pastikan service PAT valid, author MR ada di allowlist, target branch tidak protected, dan mapping branch tersedia. |
| GitLab menolak action | Periksa permission PAT user, protected branch/environment, approval GitLab, dan status pipeline di GitLab. |

## Batasan keamanan

- Jangan pernah kirim PAT di group Telegram.
- Jangan menganggap tombol Telegram melewati aturan GitLab; semua aksi tetap
  memakai PAT user yang mengklik, kecuali callback automation protected yang
  memang memakai service account konfigurasi, dan tetap dapat ditolak GitLab.
- Gunakan izin manual script secara sempit, terutama untuk job deployment dan
  branch production.
- Jangan menaruh secret pada output job karena log tetap disimpan dan dikelola
  oleh GitLab.
