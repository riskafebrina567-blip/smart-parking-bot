# 🚀 Panduan Deploy Smart Parking ke Render

## Langkah 1: Persiapan GitHub Repository

### A. Buat Repository Baru
1. Buka https://github.com
2. Login ke akun GitHub Anda
3. Klik tombol **"+"** di kanan atas → **"New repository"**
4. Isi detail:
   - Repository name: `smart-parking-bot`
   - Description: `Smart Parking System dengan Telegram Bot`
   - Pilih **Public**
   - ✅ Centang "Add a README file"
5. Klik **"Create repository"**

### B. Upload File ke GitHub
1. Di halaman repository, klik **"Add file"** → **"Upload files"**
2. Upload 3 file berikut:
   - `app.py`
   - `requirements.txt`
   - `render.yaml`
3. Scroll ke bawah, klik **"Commit changes"**

---

## Langkah 2: Daftar & Setup Render

### A. Buat Akun Render
1. Buka https://render.com
2. Klik **"Get Started for Free"**
3. Pilih **"GitHub"** untuk sign up (lebih mudah)
4. Authorize Render untuk akses GitHub Anda

### B. Buat Web Service Baru
1. Di Dashboard Render, klik **"New +"** → **"Web Service"**
2. Pilih **"Build and deploy from a Git repository"** → **Next**
3. Klik **"Connect"** pada repository `smart-parking-bot`
4. Isi konfigurasi:

| Field | Value |
|-------|-------|
| Name | `smart-parking-bot` |
| Region | `Singapore (Southeast Asia)` |
| Branch | `main` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT` |
| Instance Type | **Free** |

5. Klik **"Create Web Service"**

### C. Tunggu Deployment
- Render akan mulai build aplikasi
- Tunggu sampai status berubah jadi **"Live"** ✅
- Catat URL yang diberikan, contoh: `https://smart-parking-bot.onrender.com`

---

## Langkah 3: Update URL di Kode

### ⚠️ PENTING: Ganti WEBHOOK_URL

1. Di GitHub, buka file `app.py`
2. Klik ikon **pensil** (Edit)
3. Cari baris ini (sekitar baris 8):
   ```python
   WEBHOOK_URL = 'https://smart-parking-bot.onrender.com'
   ```
4. Ganti dengan URL Render Anda yang asli
5. Klik **"Commit changes"**
6. Render akan otomatis redeploy

---

## Langkah 4: Aktifkan Webhook Telegram

Setelah deployment selesai dan URL sudah benar:

1. Buka browser
2. Akses URL ini (ganti dengan URL Anda):
   ```
   https://smart-parking-bot.onrender.com/set_webhook
   ```
3. Jika berhasil, akan muncul:
   ```json
   {
     "status": "success",
     "message": "Webhook setup successful"
   }
   ```

---

## Langkah 5: Test Bot Telegram

1. Buka Telegram
2. Cari bot: `@NamaBotAnda` (sesuai yang Anda buat di BotFather)
3. Klik **Start** atau ketik `/start`
4. Coba fitur:
   - Klik "Cek Ketersediaan 🅿️"
   - Ketik `/book A1`
   - Ketik `/cancel A1`

---

## Langkah 6: Setup Keep-Alive (Agar Tidak Sleep)

Render free tier akan sleep setelah 15 menit tidak ada aktivitas. Solusinya:

### Gunakan UptimeRobot (Gratis)
1. Buka https://uptimerobot.com
2. Daftar akun gratis
3. Klik **"Add New Monitor"**
4. Isi:
   - Monitor Type: `HTTP(s)`
   - Friendly Name: `Smart Parking Bot`
   - URL: `https://smart-parking-bot.onrender.com/ping`
   - Monitoring Interval: `5 minutes`
5. Klik **"Create Monitor"**

Sekarang UptimeRobot akan ping server setiap 5 menit, mencegah sleep!

---

## Langkah 7: Update Wokwi

Ubah URL di kode Wokwi ESP32:

```cpp
const char* serverUrl = "https://smart-parking-bot.onrender.com/update_sensors";
const char* apiKey = "smartparking2024";
```

---

## 📋 Checklist Deployment

- [ ] Repository GitHub dibuat
- [ ] 3 file diupload (app.py, requirements.txt, render.yaml)
- [ ] Web Service Render dibuat
- [ ] Status Render = "Live"
- [ ] WEBHOOK_URL di app.py sudah diganti dengan URL asli
- [ ] Webhook Telegram diaktifkan (/set_webhook)
- [ ] Bot Telegram bisa diakses
- [ ] UptimeRobot dikonfigurasi
- [ ] Wokwi URL diupdate

---

## 🔧 Troubleshooting

### Bot tidak merespon
1. Cek apakah Render status = "Live"
2. Cek Log di Render Dashboard
3. Pastikan webhook sudah diset: akses `/set_webhook` lagi

### Error 401 dari Wokwi
- Pastikan header `X-API-Key: smartparking2024` sudah ditambahkan

### Render terus Sleep
- Pastikan UptimeRobot sudah aktif
- Cek interval ping = 5 menit

### Deployment gagal
- Cek requirements.txt sudah benar
- Lihat error di Build Logs Render

---

## 📊 Endpoint API

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/` | GET | Status server |
| `/health` | GET | Health check |
| `/ping` | GET | Keep-alive |
| `/slots` | GET | Status semua slot |
| `/set_webhook` | GET | Setup webhook Telegram |
| `/update_sensor` | POST | Update 1 sensor |
| `/update_sensors` | POST | Update banyak sensor |

---

## 🎉 Selesai!

Sistem Smart Parking Anda sekarang online dan bisa diakses dari mana saja!

- **Telegram Bot**: Untuk user booking parkir
- **Wokwi/ESP32**: Untuk sensor deteksi kendaraan
- **Render**: Server yang hosting semuanya
