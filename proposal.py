# -*- coding: utf-8 -*-
"""
Генерация текста коммерческого предложения по данным клиента.
Несколько шаблонов с разным тоном; можно добавлять новые.
"""

from datetime import date


# Список шаблонов для выбора в форме (id → название)
TEMPLATES = {
    "classic": "Классический — деловой тон",
    "partner": "Партнёрский — тёплый, доверительный",
    "benefit": "С акцентом на выгоду — результат и цифры",
    "short": "Краткий и убедительный — по делу",
}


def generate_proposal(client: dict, template_id: str = "classic") -> str:
    """
    Формирует текст КП по данным клиента и выбранному шаблону.
    client: name, company, contact, subject.
    """
    today = date.today().strftime("%d.%m.%Y")
    name = client.get("name", "")
    company = client.get("company", "")
    contact = client.get("contact", "")
    subject = client.get("subject", "")

    template_id = template_id if template_id in TEMPLATES else "classic"
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
    """Деловой, нейтральный тон."""
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
    """Тёплый, партнёрский тон."""
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
    """Акцент на выгоде и результате."""
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
    """Кратко и по делу."""
    return f"""КП от {today}

{name}, {company}

Тема: {subject}
Контакт: {contact}

Предложение готово. Обсудим условия и сроки — свяжитесь с нами.

С уважением,
Команда""".strip()
