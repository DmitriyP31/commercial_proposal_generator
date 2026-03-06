# -*- coding: utf-8 -*-
"""
Генерация текста коммерческого предложения по данным клиента.
Модуль можно расширять: добавлять поля в шаблон или новые шаблоны.
"""

from datetime import date


def generate_proposal(client: dict) -> str:
    """
    Формирует текст КП из переданных данных о клиенте.
    client — словарь с ключами: name, company, contact, subject (и при необходимости другие).
    """
    today = date.today().strftime("%d.%m.%Y")
    name = client.get("name", "")
    company = client.get("company", "")
    contact = client.get("contact", "")
    subject = client.get("subject", "")

    text = f"""КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ
от {today}

Уважаемый(ая) {name}!

Компания направляет Вам коммерческое предложение по запросу.

Получатель: {company}
Контакт: {contact}

Тема предложения: {subject}

Мы готовы обсудить условия и сроки. Для уточнения деталей свяжитесь с нами.

С уважением,
Команда"""
    return text.strip()
