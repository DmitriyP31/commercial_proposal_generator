# -*- coding: utf-8 -*-
"""
Генератор коммерческих предложений — минимальная версия (V1).
Маршруты: форма ввода → генерация КП → просмотр/редактирование → скачать PDF.
"""

import io
import os
from flask import Flask, request, render_template, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from proposal import generate_proposal

app = Flask(__name__)

# Подключение шрифта для кириллицы: пробуем Arial (Windows), иначе DejaVu в папке проекта
def _get_pdf_font():
    arial_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
    if os.path.isfile(arial_path):
        pdfmetrics.registerFont(TTFont("PdfFont", arial_path))
        return "PdfFont"
    dejavu = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
    if os.path.isfile(dejavu):
        pdfmetrics.registerFont(TTFont("PdfFont", dejavu))
        return "PdfFont"
    return "Helvetica"  # только латиница


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
    """Главная: форма для ввода данных о клиенте."""
    return render_template("index.html", proposal_text=None, edit_mode=False)


@app.route("/generate", methods=["POST"])
def generate():
    """Принимает данные формы, генерирует текст КП и показывает его для просмотра/редактирования."""
    client = {
        "name": request.form.get("name", "").strip(),
        "company": request.form.get("company", "").strip(),
        "contact": request.form.get("contact", "").strip(),
        "subject": request.form.get("subject", "").strip(),
    }
    proposal_text = generate_proposal(client)
    return render_template("index.html", proposal_text=proposal_text, edit_mode=True)


@app.route("/download", methods=["POST"])
def download_pdf():
    """
    Получает итоговый текст КП из формы (после возможного редактирования)
    и отдаёт PDF файлом.
    """
    text = request.form.get("proposal_text", "")
    if not text.strip():
        return "Текст предложения пуст. Сгенерируйте КП и при необходимости отредактируйте его.", 400

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
