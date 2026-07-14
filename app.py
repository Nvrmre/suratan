import json
import uuid
import shutil
from flask import Flask, render_template, request, send_file
from weasyprint import HTML
import os
import base64
import io
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
GENERATED_DIR = os.path.join(os.path.dirname(__file__), 'generated')
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

LETTER_TYPES = {
    'umum': 'Surat Resmi Umum',
    'penawaran': 'Surat Penawaran',
    'lamaran': 'Surat Lamaran Kerja',
    'undangan': 'Surat Undangan',
    'pemberitahuan': 'Surat Pemberitahuan',
}


@app.template_filter('fromjson')
def fromjson_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def has_table_data(raw):
    try:
        data = json.loads(raw)
        if not data or not isinstance(data, list) or len(data) < 1:
            return False
        has_content = False
        for row in data:
            for cell in row:
                if isinstance(cell, str) and cell.strip():
                    has_content = True
                    break
            if has_content:
                break
        return has_content
    except (json.JSONDecodeError, TypeError):
        return False


@app.route('/')
def index():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', letter_types=LETTER_TYPES, today=today)


def collect_form_data():
    d = {}
    for field in ['company_name', 'company_address', 'company_phone', 'company_email', 'company_website',
                  'letter_type', 'recipient', 'recipient_address', 'sender', 'sender_title',
                  'subject', 'body', 'table_data', 'position', 'event_name', 'event_date',
                  'event_time', 'event_place', 'date']:
        d[field] = request.form.get(field, '')

    logo_b64 = None
    logo = request.files.get('logo')
    if logo and logo.filename:
        logo_b64 = _img_to_b64(logo)
    elif request.form.get('logo_b64'):
        logo_b64 = request.form.get('logo_b64')

    sig_b64 = None
    ttd = request.files.get('signature')
    if ttd and ttd.filename:
        sig_b64 = _img_to_b64(ttd)
    elif request.form.get('signature_b64'):
        sig_b64 = request.form.get('signature_b64')

    d['logo_b64'] = logo_b64
    d['signature_b64'] = sig_b64
    return d


def render_letter_html(d):
    date_formatted = _format_date(d['date'])
    letter_type_label = LETTER_TYPES.get(d['letter_type'], 'Surat Resmi')

    return render_template(
        'letter.html',
        company_name=d['company_name'].strip(),
        company_address=d['company_address'].strip(),
        company_phone=d['company_phone'].strip(),
        company_email=d['company_email'].strip(),
        company_website=d['company_website'].strip(),
        letter_type=d['letter_type'],
        letter_type_label=letter_type_label,
        recipient=d['recipient'].strip(),
        recipient_address=d['recipient_address'].strip(),
        sender=d['sender'].strip(),
        sender_title=d['sender_title'].strip(),
        subject=d['subject'].strip(),
        body=d['body'].strip(),
        date=date_formatted,
        date_str=d['date'],
        logo_b64=d['logo_b64'],
        signature_b64=d['signature_b64'],
        table_data=d['table_data'],
        position=d['position'].strip(),
        event_name=d['event_name'].strip(),
        event_date=d['event_date'].strip(),
        event_time=d['event_time'].strip(),
        event_place=d['event_place'].strip(),
        show_table=has_table_data(d['table_data']),
    )


@app.route('/generate', methods=['POST'])
def generate():
    d = collect_form_data()
    html_content = render_letter_html(d)

    filename = f'surat_{d["letter_type"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    filepath = os.path.join(GENERATED_DIR, filename)
    HTML(string=html_content).write_pdf(filepath)
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route('/preview', methods=['POST'])
def preview():
    d = collect_form_data()
    html_content = render_letter_html(d)

    token = uuid.uuid4().hex[:12]
    token_dir = os.path.join(TEMP_DIR, token)
    os.makedirs(token_dir, exist_ok=True)

    with open(os.path.join(token_dir, 'data.json'), 'w') as f:
        json.dump(d, f)

    if d['logo_b64']:
        logo_path = os.path.join(token_dir, 'logo.txt')
        with open(logo_path, 'w') as f:
            f.write(d['logo_b64'])
    if d['signature_b64']:
        sig_path = os.path.join(token_dir, 'sig.txt')
        with open(sig_path, 'w') as f:
            f.write(d['signature_b64'])

    return render_template('preview.html', letter_html=html_content, token=token)


@app.route('/generate_from_token/<token>')
def generate_from_token(token):
    token_dir = os.path.join(TEMP_DIR, token)
    data_path = os.path.join(token_dir, 'data.json')
    if not os.path.exists(data_path):
        return 'Token tidak valid', 404

    with open(data_path) as f:
        d = json.load(f)

    logo_path = os.path.join(token_dir, 'logo.txt')
    if os.path.exists(logo_path):
        with open(logo_path) as f:
            d['logo_b64'] = f.read()
    sig_path = os.path.join(token_dir, 'sig.txt')
    if os.path.exists(sig_path):
        with open(sig_path) as f:
            d['signature_b64'] = f.read()

    html_content = render_letter_html(d)

    filename = f'surat_{d["letter_type"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    filepath = os.path.join(GENERATED_DIR, filename)
    HTML(string=html_content).write_pdf(filepath)

    shutil.rmtree(token_dir, ignore_errors=True)

    return send_file(filepath, as_attachment=True, download_name=filename)


def _img_to_b64(file):
    img = Image.open(file.stream).convert('RGBA')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return f'data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}'


def _format_date(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        bulan = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        return f'{dt.day} {bulan[dt.month - 1]} {dt.year}'
    except (ValueError, IndexError):
        return date_str


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
