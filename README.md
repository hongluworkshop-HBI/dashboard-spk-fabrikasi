# Dashboard SPK Fabrikasi 2026

Dashboard Streamlit bilingual Indonesia–Mandarin untuk analisa SPK fabrikasi.

## Arsitektur
Google Sheets / Google Drive → Streamlit Community Cloud → OpenAI API / AI Analyst

## Fitur
- KPI Total SPK
- Total Proyek
- Total Vendor
- Total/Selesai/Sisa Tonase
- Progress total dan progress tagihan
- Top proyek dan vendor
- Analisa area dan bulan
- SPK dengan sisa tonase terbesar
- Profil dengan tonase terbesar
- AI Analyst

## Sumber Data
Aplikasi membaca worksheet `RINGKASAN` dari spreadsheet
`DATABASE SPK FABRIKASI 2026 - DASHBOARD ANALISA`.

Data dicache 5 menit dan tersedia tombol Refresh.

## Langkah Deploy
1. Buat repository GitHub `dashboard-spk-fabrikasi-2026`.
2. Upload semua file dalam paket ini.
3. Di Google Cloud, enable Google Sheets API.
4. Buat Service Account dan JSON key.
5. Share Google Sheet ke email Service Account sebagai Viewer.
6. Buat OpenAI API key.
7. Di Streamlit Community Cloud, buka App → Settings → Secrets.
8. Gunakan `.streamlit/secrets.toml.example` sebagai template.
9. Deploy `streamlit_app.py`.

## Keamanan
Jangan upload `secrets.toml`, API key, password, atau OTP ke GitHub.
