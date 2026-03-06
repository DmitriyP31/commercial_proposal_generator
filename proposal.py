# -*- coding: utf-8 -*-
"""
Модуль генерации текста коммерческого предложения (КП).

Используется в app.py:
  - TEMPLATES — список шаблонов для выбора в форме (id и название)
  - generate_proposal(client, template_id) — возвращает готовый текст КП
"""

from datetime import date

# Шаблоны КП: идентификатор → название для выпадающего списка в форме
TEMPLATES = {
    "classic": "Классический — деловой тон",
    "partner": "Партнёрский — тёплый, доверительный",
    "benefit": "С акцентом на выгоду — результат и цифры",
    "short": "Краткий и убедительный — по делу",
}


def generate_proposal(client, template_id="classic"):
    """
    Собирает текст КП из данных клиента и выбранного шаблона.

    client — словарь с ключами: name, company, contact, subject.
    template_id — один из ключей TEMPLATES (если передан другой — используется "classic").
    Возвращает строку с текстом КП.
    """
    today = date.today().strftime("%d.%m.%Y")
    name = client.get("name", "")
    company = client.get("company", "")
    contact = client.get("contact", "")
    subject = client.get("subject", "")

    # Если передан неизвестный шаблон — берём классический
    if template_id not in TEMPLATES:
        template_id = "classic"

    if template_id == "classic":
        return _template_classic(today, name, company, contact, subject)
    if template_id == "partner":
        return _template_partner(today, name, company, contact, subject)
    if template_id == "benefit":
        return _template_benefit(today, name, company, contact, subject)
    if template_id == "short":
        return _template_short(today, name, company, contact, subject)

    return _template_classic(today, name, company, contact, subject)


def _template_classic(today, name, company, contact, subject):
    """Шаблон: деловой, нейтральный тон."""
    return f"""КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ
от {today}

Уважаемый(ая) {name}!

Направляем Вам коммерческое предложение в ответ на ваш запрос.

Получатель: {company}
Контакт: {contact}

Тема: {subject}

Мы готовы обсудить условия, сроки и индивидуальные скидки. Для согласования деталей свяжитесь с нами в удобное время.

С уважением,
Команда""".strip()


def _template_partner(today, name, company, contact, subject):
    """Шаблон: тёплый, партнёрский тон."""
    return f"""КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ
от {today}

{name}, добрый день!

Рады предложить вам решение по теме «{subject}» для {company}.

Контакт для связи: {contact}

Мы ценим долгосрочное сотрудничество и готовы подстроиться под ваши сроки и бюджет. Давайте обсудим, как лучше реализовать проект — ответьте на это письмо или позвоните нам.

Будем рады помочь.

С уважением,
Команда""".strip()


def _template_benefit(today, name, company, contact, subject):
    """Шаблон: акцент на выгоде и результате."""
    return f"""КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ
от {today}

Уважаемый(ая) {name}!

{company} получает выгодное предложение по направлению: {subject}.

Контакт: {contact}

Что вы получаете: прозрачные условия, фиксированные сроки и поддержку на всех этапах. Многие клиенты уже сократили издержки и ускорили процессы с нашим решением.

Готовы обсудить детали и рассчитать точную стоимость под ваши задачи. Напишите или позвоните — ответим в течение одного рабочего дня.

С уважением,
Команда""".strip()


def _template_short(today, name, company, contact, subject):
    """Шаблон: кратко и по делу."""
    return f"""КП от {today}

{name}, {company}

Тема: {subject}
Контакт: {contact}

Предложение готово. Обсудим условия и сроки — свяжитесь с нами.

С уважением,
Команда""".strip()
