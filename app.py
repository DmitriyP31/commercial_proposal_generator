# -*- coding: utf-8 -*-
"""
Генератор коммерческих предложений (V2).

Как устроен файл:
  1. Константы (лимиты, путь к файлу сохранённых КП)
  2. Хранение: чтение/запись JSON-файла
  3. Вспомогательные функции (шрифт, очистка текста, отрисовка PDF)
  4. Маршруты: главная, генерация, скачать/сохранить, список, просмотр
"""

import io
import json
import os
import uuid
from datetime import datetime
from flask import Flask, request, render_template, send_file, redirect, url_for, abort
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from proposal import generate_proposal, TEMPLATES

app = Flask(__name__)

# --- Константы (удобно менять в одном месте) ---
MAX_FIELD_LEN = 500          # макс. длина каждого поля формы (символов)
MAX_PROPOSAL_LEN = 100_000   # макс. длина текста КП при скачивании PDF
STORAGE_FILE = os.path.join(os.path.dirname(__file__), "saved_proposals.json")

# Кэш имени шрифта: регистрируем один раз, дальше только возвращаем имя
_cached_font_name = None


def _load_proposals():
    """Читает список сохранённых КП из файла. Если файла нет или он пустой/повреждён — возвращает пустой список."""
    if not os.path.isfile(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


def _save_proposals(proposals):
    """Записывает список КП в файл."""
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(proposals, f, ensure_ascii=False, indent=2)


def _add_proposal(text, title=None):
    """Добавляет новое КП. title — название в списке; если не задано — берётся первая строка текста. Возвращает id."""
    proposals = _load_proposals()
    raw_title = (title or "").strip()
    if not raw_title:
        first_line = (text or "").strip().split("\n")[0][:80]
        raw_title = first_line or "Без названия"
    new_id = str(uuid.uuid4())[:8]
    new_item = {
        "id": new_id,
        "title": raw_title,
        "text": text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    proposals.append(new_item)
    _save_proposals(proposals)
    return new_id


def _get_proposal_by_id(proposal_id):
    """Возвращает словарь КП по id или None."""
    for item in _load_proposals():
        if item.get("id") == proposal_id:
            return item
    return None


def _get_pdf_font():
    """
    Возвращает имя шрифта для PDF. Кириллица поддерживается через Arial (Windows)
    или DejaVu (файл в папке проекта). Если ничего нет — Helvetica (только латиница).
    """
    global _cached_font_name
    if _cached_font_name is not None:
        return _cached_font_name

    # Сначала пробуем Arial — он есть в Windows
    windows_dir = os.environ.get("WINDIR", "C:\\Windows")
    arial_path = os.path.join(windows_dir, "Fonts", "arial.ttf")
    if os.path.isfile(arial_path):
        pdfmetrics.registerFont(TTFont("PdfFont", arial_path))
        _cached_font_name = "PdfFont"
        return _cached_font_name

    # Иначе — шрифт DejaVu в папке с приложением
    project_dir = os.path.dirname(__file__)
    dejavu_path = os.path.join(project_dir, "DejaVuSans.ttf")
    if os.path.isfile(dejavu_path):
        pdfmetrics.registerFont(TTFont("PdfFont", dejavu_path))
        _cached_font_name = "PdfFont"
        return _cached_font_name

    # Запасной вариант: только латиница
    _cached_font_name = "Helvetica"
    return _cached_font_name


def _sanitize_text_for_pdf(text):
    """
    Убирает из текста управляющие символы (кроме переноса строки и табуляции).
    Иначе библиотека PDF может выдать ошибку при отрисовке.
    """
    result = []
    for char in text:
        if char in "\n\r\t":
            result.append(char)
        elif ord(char) >= 32:
            result.append(char)
    return "".join(result)


def _iter_draw_chunks(text, max_chunk=80):
    """
    Разбивает текст на части для построчной отрисовки в PDF.
    Длинные строки режет на куски по max_chunk символов.
    yield None — значит «пустая строка» (отступ между абзацами).
    """
    # Приводим все переносы к \n
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    for line in lines:
        # Режем длинную строку на куски
        start = 0
        while start < len(line):
            chunk = line[start : start + max_chunk]
            yield chunk
            start += max_chunk
        # После каждой строки — отступ (пустая строка)
        yield None


def _draw_text_on_canvas(pdf_canvas, text, font_name, page_layout):
    """
    Пишет текст на странице PDF. При нехватке места — создаёт новую страницу.
    page_layout — словарь с ключами: width, height, margin, line_height, max_chunk.
    """
    margin = page_layout["margin"]
    line_height = page_layout["line_height"]
    page_height = page_layout["height"]

    x = margin
    y = page_height - margin

    for chunk in _iter_draw_chunks(text, page_layout["max_chunk"]):
        # Нужна новая страница?
        if y < margin:
            pdf_canvas.showPage()
            pdf_canvas.setFont(font_name, 12)
            y = page_height - margin

        if chunk is None:
            y -= 4
            continue

        pdf_canvas.drawString(x, y, chunk)
        y -= line_height


def _build_pdf_response(text, download_name="commercial_proposal.pdf"):
    """Собирает PDF из текста и отдаёт ответ для скачивания. Используется и с главной, и со страницы сохранённого КП."""
    text = _sanitize_text_for_pdf(text)
    buffer = io.BytesIO()
    font_name = _get_pdf_font()
    pdf_canvas = canvas.Canvas(buffer, pagesize=A4)
    pdf_canvas.setFont(font_name, 12)
    width, height = A4
    page_layout = {"width": width, "height": height, "margin": 50, "line_height": 16, "max_chunk": 80}
    _draw_text_on_canvas(pdf_canvas, text, font_name, page_layout)
    pdf_canvas.save()
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=download_name)


def _render_form_page(proposal_text=None, error=None):
    """Общие параметры для страницы с формой (при загрузке и при ошибке)."""
    return render_template(
        "index.html",
        proposal_text=proposal_text,
        edit_mode=(proposal_text is not None),
        templates=TEMPLATES,
        error=error,
    )


CLIENT_FIELD_LABELS = {
    "name": "Контактное лицо",
    "company": "Компания",
    "contact": "Контакт",
    "subject": "Тема предложения",
}


def _build_client_from_request(form):
    """Возвращает словарь данных клиента из полей формы с обрезанными пробелами."""
    return {
        "name": form.get("name", "").strip(),
        "company": form.get("company", "").strip(),
        "contact": form.get("contact", "").strip(),
        "subject": form.get("subject", "").strip(),
    }


def _validate_client_required_fields(client):
    """Проверяет, что все обязательные поля заполнены. Возвращает текст ошибки или None."""
    empty_fields = [key for key, value in client.items() if not value]
    if not empty_fields:
        return None
    labels_list = [CLIENT_FIELD_LABELS[key] for key in empty_fields]
    return "Заполните все поля: " + ", ".join(labels_list)


def _validate_client_field_lengths(client):
    """Проверяет, что длина каждого поля не превышает лимит. Возвращает текст ошибки или None."""
    for field_name, value in client.items():
        if len(value) > MAX_FIELD_LEN:
            return f"Поле «{field_name}» слишком длинное (макс. {MAX_FIELD_LEN} символов)."
    return None


# --- Маршруты (что делает каждая страница) ---

@app.route("/")
def index():
    """Главная страница: показываем форму для ввода данных клиента и выбора шаблона."""
    return _render_form_page(proposal_text=None, error=None)


@app.route("/generate", methods=["POST"])
def generate():
    """Получаем данные формы, проверяем их, генерируем текст КП и показываем его для редактирования."""
    client = _build_client_from_request(request.form)

    error_message = _validate_client_required_fields(client)
    if error_message is not None:
        return _render_form_page(error=error_message), 400

    error_message = _validate_client_field_lengths(client)
    if error_message is not None:
        return _render_form_page(error=error_message), 400

    # Проверка: выбран существующий шаблон
    template_id = request.form.get("template_id", "classic")
    if template_id not in TEMPLATES:
        return _render_form_page(error="Выбран неверный шаблон КП. Выберите шаблон из списка."), 400

    # Генерируем текст КП и показываем страницу с формой и блоком редактирования
    proposal_text = generate_proposal(client, template_id=template_id)
    return _render_form_page(proposal_text=proposal_text, error=None)


@app.route("/proposal_action", methods=["POST"])
def proposal_action():
    """Одна форма с двумя кнопками: «Скачать PDF» или «Сохранить в список». По полю action решаем, что делать."""
    text = request.form.get("proposal_text", "")
    action = request.form.get("action", "")

    if not text.strip():
        return _render_form_page(proposal_text=text, error="Текст предложения пуст. Сгенерируйте КП и при необходимости отредактируйте его."), 400
    if len(text) > MAX_PROPOSAL_LEN:
        return _render_form_page(proposal_text=text, error=f"Текст КП слишком длинный (макс. {MAX_PROPOSAL_LEN} символов)."), 400

    if action == "save":
        title = request.form.get("save_title", "").strip()
        new_id = _add_proposal(text, title=title or None)
        return redirect(url_for("view_proposal", proposal_id=new_id))
    return _build_pdf_response(text)


@app.route("/saved/")
def list_proposals():
    """Страница со списком сохранённых КП (новые сверху)."""
    proposals = list(reversed(_load_proposals()))
    return render_template("list.html", proposals=proposals)


@app.route("/saved/<proposal_id>")
def view_proposal(proposal_id):
    """Просмотр одного сохранённого КП."""
    item = _get_proposal_by_id(proposal_id)
    if item is None:
        abort(404)
    return render_template("view.html", proposal=item)


@app.route("/saved/<proposal_id>/pdf")
def download_saved_pdf(proposal_id):
    """Скачать сохранённое КП в виде PDF."""
    item = _get_proposal_by_id(proposal_id)
    if item is None:
        abort(404)
    safe_title = "".join(c for c in (item.get("title") or "proposal")[:30] if c.isalnum() or c in " _-")
    return _build_pdf_response(item["text"], download_name=f"КП_{safe_title or 'proposal'}.pdf")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
