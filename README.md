# Suratan - Aplikasi Pembuat Surat

Web app untuk membuat surat resmi dengan kop surat sendiri, tabel, dan tanda tangan. Output dalam format PDF ukuran A4.

## Fitur

- 5 jenis surat: Umum, Penawaran, Lamaran Kerja, Undangan, Pemberitahuan
- Kop surat dinamis (nama perusahaan, alamat, kontak, logo)
- Upload logo & tanda tangan (PNG transparan)
- Tabel dinamis dalam surat
- Preview surat sebelum download
- Output PDF A4

## Tech Stack

- Python Flask
- WeasyPrint (HTML to PDF)
- Gunicorn
- Nginx (reverse proxy)

## Cara Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask weasyprint gunicorn Pillow
python3 app.py
```

Buka `http://localhost:5000`
