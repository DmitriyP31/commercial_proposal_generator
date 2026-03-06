# -*- coding: utf-8 -*-
"""
Генератор коммерческих предложений — V2.
Форма → выбор шаблона КП → генерация → просмотр/редактирование → скачать PDF.
"""

import io
import os
from flask import Flask, request, render_template, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from proposal import generate_proposal, TEMPLATES

app = Flask(__name__)

# Лимиты для проверки крайних случаев
MAX_FIELD_LEN = 500
MAX_PROPOSAL_LEN = 100_000

# Кэш зарегистрированного шрифта, чтобы не регистрировать повторно (крайний случай: повторный вызов)
_pdf_font_registered = None

# Подключение шрифта для кириллицы: пробуем Arial (Windows), иначе DejaVu в папке проекта
def _get_pdf_font():
    global _pdf_font_registered
    if _pdf_font_registered is not None:
        return _pdf_font_registered
    arial_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
    if os.path.isfile(arial_path):
        pdfmetrics.registerFont(TTFont("PdfFont", arial_path))
        _pdf_font_registered = "PdfFont"
        return _pdf_font_registered
    dejavu = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
    if os.path.isfile(dejavu):
        pdfmetrics.registerFont(TTFont("PdfFont", dejavu))
        _pdf_font_registered = "PdfFont"
        return _pdf_font_registered
    _pdf_font_registered = "Helvetica"
    return _pdf_font_registered


def _sanitize_text_for_pdf(text: str) -> str:
    """Удаляет управляющие символы (кроме \\n, \\r, \\t), чтобы PDF не падал (крайний случай)."""
    return "".join(c for c in text if c in "\n\r\t" or ord(c) >= 32)


def _iter_draw_chunks(text, max_chunk=80):
    """Разбивает текст на строки и длинные строки — на куски по max_chunk символов (для вывода в PDF)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for line in lines:
        start = 0
        while start < len(line):
            yield line[start : start + max_chunk]
            start += max_chunk
        yield None  # пустая строка после линии (отступ)

def _draw_text_on_canvas(c, text, font_name, page):
    """
    Рисует текст на canvas. page — dict: width, height, margin, line_height, max_chunk.
    """
    m = page["margin"]
    lh = page["line_height"]
    x, y = m, page["height"] - m
    for chunk in _iter_draw_chunks(text, page["max_chunk"]):
        if y < m:
            c.showPage()
            c.setFont(font_name, 12)
            y = page["height"] - m
        if chunk is None:
            y -= 4
            continue
        c.drawString(x, y, chunk)
        y -= lh


@app.route("/")
def index():
    """Главная: форма для ввода данных о клиенте и выбора шаблона КП."""
    return render_template("index.html", proposal_text=None, edit_mode=False, templates=TEMPLATES, error=None)


@app.route("/generate", methods=["POST"])
def generate():
    """Принимает данные формы и template_id, генерирует текст КП, показывает для просмотра/редактирования."""
    # Крайний случай 1: пустые или только пробелы в обязательных полях
    client = {
        "name": request.form.get("name", "").strip(),
        "company": request.form.get("company", "").strip(),
        "contact": request.form.get("contact", "").strip(),
        "subject": request.form.get("subject", "").strip(),
    }
    empty = [k for k, v in client.items() if not v]
    if empty:
        names = {"name": "Контактное лицо", "company": "Компания", "contact": "Контакт", "subject": "Тема предложения"}
        msg = "Заполните все поля: " + ", ".join(names[k] for k in empty)
        return render_template("index.html", proposal_text=None, edit_mode=False, templates=TEMPLATES, error=msg), 400

    # Крайний случай 2: слишком длинные значения полей
    for key, value in client.items():
        if len(value) > MAX_FIELD_LEN:
            return render_template(
                "index.html", proposal_text=None, edit_mode=False, templates=TEMPLATES,
                error=f"Поле «{key}» слишком длинное (макс. {MAX_FIELD_LEN} символов)."
            ), 400

    # Крайний случай 3: неверный template_id
    template_id = request.form.get("template_id", "classic")
    if template_id not in TEMPLATES:
        return render_template(
            "index.html", proposal_text=None, edit_mode=False, templates=TEMPLATES,
            error="Выбран неверный шаблон КП. Выберите шаблон из списка."
        ), 400

    proposal_text = generate_proposal(client, template_id=template_id)
    return render_template("index.html", proposal_text=proposal_text, edit_mode=True, templates=TEMPLATES, error=None)


@app.route("/download", methods=["POST"])
def download_pdf():
    """
    Получает итоговый текст КП из формы (после возможного редактирования)
    и отдаёт PDF файлом.
    """
    text = request.form.get("proposal_text", "")
    # Крайний случай 4: пустой или только пробелы текст при скачивании
    if not text.strip():
        return "Текст предложения пуст. Сгенерируйте КП и при необходимости отредактируйте его.", 400
    # Крайний случай 5: слишком длинный текст (защита от переполнения памяти/PDF)
    if len(text) > MAX_PROPOSAL_LEN:
        return f"Текст КП слишком длинный (макс. {MAX_PROPOSAL_LEN} символов). Сократите или разбейте на части.", 400
    # Крайний случай 5б: управляющие символы в тексте могут ломать PDF — оставляем только печатные и \\n\\r\\t
    text = _sanitize_text_for_pdf(text)

    # Формируем PDF в памяти (без сохранения файла на диск)
    buffer = io.BytesIO()
    font_name = _get_pdf_font()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont(font_name, 12)
    width, height = A4
    page = {"width": width, "height": height, "margin": 50, "line_height": 16, "max_chunk": 80}
    _draw_text_on_canvas(c, text, font_name, page)
    c.save()
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="commercial_proposal.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
