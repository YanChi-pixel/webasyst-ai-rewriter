# -*- coding: utf-8 -*-
"""Собирает обезличенный датасет «переписывание карточек товаров» (RU).

Берёт правила и few-shot примеры из prompts/ (того же репозитория), подаёт их в
LLM как системный промпт и генерирует синтетические карточки по короткому блоку
фактов. Ни одного реального названия/артикула/домена клиента: вся предметная
информация — вымышленная.

    python hf/build_dataset.py --limit 24
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
HF = REPO / "hf"
PROMPTS = REPO / "prompts"
OUT = HF / "data" / "rewrites.jsonl"
PARENT_ENV = REPO.parent / ".env"  # D:\AI Projects\webasyst\.env


def load_env() -> dict:
    env: dict = {}
    if PARENT_ENV.exists():
        for line in PARENT_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


_ENV = load_env()
BASE = os.environ.get("LLM_API_BASE", _ENV.get("LLM_API_BASE", "https://api.deepseek.com"))
KEY = os.environ.get("LLM_API_KEY", _ENV.get("LLM_API_KEY", ""))
MODEL = os.environ.get("LLM_MODEL", _ENV.get("LLM_MODEL", "deepseek-chat"))

# Локальный fallback: Ollama (та же модель, которой пайплайн писал в офлайн-режиме).
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", _ENV.get("OLLAMA_BASE_URL", "http://localhost:11434"))
OLLAMA_WRITER = os.environ.get("OLLAMA_WRITER_MODEL", _ENV.get("OLLAMA_WRITER_MODEL", "qwen2.5:14b"))
OLLAMA_NUM_CTX = int(_ENV.get("OLLAMA_NUM_CTX", "16384"))

# Каждая строка — один синтетический «Ввод», как его видела модель в пайплайне.
FACTS = [
    # ---- ткани и текстиль ----
    ("textile", "Ткань для столового белья «Атлас-Люкс» 07А-ЖКгл+ГОМ 2222/010101, состав 35% хлопок/65% полиэфир, плотность 210 г/м², ширина 150 см, рулон 50 м, переплетение жаккардовое, цвет белый, рисунок «клетка» 2222, отделка ГОМ (грязеотталкивающая маслостойкая)."),
    ("textile", "Ткань портьерная «Люмен» 09П-ЖК 3188/050505, состав 100% полиэфир, плотность 300 г/м², ширина 280 см, рулон 30 м, переплетение саржевое, цвет графитовый, отделка блэкаут."),
    ("textile", "Салфетка сервировочная «Кантри» 45×45 см, состав 100% лён, плотность 240 г/м², цвет натуральный, кромка обработана, упаковка 10 шт."),
    ("textile", "Полотенце махровое «Люкс Терри» 70×140 см, состав 100% хлопок, плотность 450 г/м², цвет белый, петля одинарная, окантовка жаккардовая."),
    ("textile", "Ткань костюмная «Формат» 08К-С 4477/090909, состав 45% шерсть/55% полиэфир, плотность 260 г/м², ширина 150 см, переплетение полотняное, цвет тёмно-серый, рисунок гладкий."),
    ("textile", "Скатерть «Торжество» 140×220 см, состав 100% полиэфир, плотность 190 г/м², цвет белый, рисунок жаккардовый «вензель», обработка краёв — подгибка."),
    ("textile", "Ткань медицинская «Гигиена» 05М-Б 5566/020202, состав 65% хлопок/35% полиэфир, плотность 150 г/м², ширина 160 см, отбеленная, отделка антистатическая."),
    ("textile", "Полотенце кухонное «Вафля» 40×60 см, состав 100% хлопок, переплетение вафельное, плотность 220 г/м², цвет белый с цветной полосой, упаковка 5 шт."),
    # ---- электроника и гаджеты ----
    ("electronics", "Портативный аккумулятор «VoltCore 10K» арт. VC-10K/PD20, ёмкость 10000 мА·ч, выход USB-C Power Delivery до 20 Вт, выход USB-A, вход USB-C, вес 210 г, корпус пластиковый, цвет чёрный, индикатор заряда."),
    ("electronics", "Настольная лампа «Люмен Про» арт. LP-3T, мощность 9 Вт, цветовая температура 3000–6000 К, три режима яркости, сенсорное управление, USB-питание, цвет белый."),
    ("electronics", "Увлажнитель воздуха «Аква» арт. AQ-300, объём 3 л, производительность 300 мл/ч, площадь до 25 м², уровень шума 28 дБ, автоотключение, цвет белый."),
    ("electronics", "Электрочайник «Классик» арт. KT-1.7, объём 1.7 л, мощность 2200 Вт, скрытый нагревательный элемент, автоотключение при закипании, корпус нержавеющая сталь."),
    ("electronics", "Фен «Стайл» арт. HD-2000, мощность 2000 Вт, два режима скорости, три режима температуры, функция холодного воздуха, съёмный фильтр, цвет чёрный."),
    ("electronics", "Смарт-розетка «Пульс» арт. SP-16A, нагрузка до 16 А, Wi-Fi 2.4 ГГц, управление с приложения, таймер, мониторинг энергопотребления, цвет белый."),
    ("electronics", "Наушники беспроводные «Эхо» арт. EB-40, Bluetooth 5.3, время работы до 40 ч с кейсом, зарядка USB-C, микрофон, защита IPX4, цвет чёрный."),
    ("electronics", "Клавиатура механическая «Тайп» арт. MK-87, 87 клавиш, переключатели красные, подсветка RGB, провод USB-C, алюминиевая верхняя панель, цвет серый."),
    # ---- мебель и интерьер ----
    ("furniture", "Кресло офисное «Эрго» арт. EG-2025, обивка дышащая сетка, газлифт 4 класса, нагрузка до 120 кг, механизм качания с фиксацией, подлокотники 3D, поясничная поддержка, цвет серый."),
    ("furniture", "Стол письменный «Лофт» арт. LT-120, столешница ЛДСП 120×60 см, каркас металлический, высота 75 см, цвет дуб сонома, нагрузка до 50 кг."),
    ("furniture", "Стеллаж «Куб» арт. ST-5, пять полок, габариты 60×30×180 см, ЛДСП 16 мм, крепление к стене, цвет белый, нагрузка на полку до 15 кг."),
    ("furniture", "Стул барный «Хай» арт. HB-75, высота сиденья 75 см, каркас металлический хромированный, сиденье из эко-кожи, цвет чёрный, нагрузка до 110 кг."),
    ("furniture", "Тумба прикроватная «Слим» арт. SN-40, габариты 40×35×50 см, два ящика, ЛДСП, фасады матовые, цвет графит, фурнитура скрытого монтажа."),
    ("furniture", "Вешалка напольная «Сто» арт. HS-12, высота 180 см, 12 крючков, основание крестообразное, материал — сталь с порошковым покрытием, цвет чёрный."),
    ("furniture", "Шкаф-купе «Простор» арт. WD-200, габариты 200×60×220 см, две двери раздвижные с зеркалом, ЛДСП, внутренняя штанга и две полки, цвет белый."),
    ("furniture", "Стол обеденный «Семья» арт. DN-140, столешница 140×80 см из МДФ с шпоном дуба, ножки металлические, высота 75 см, нагрузка до 80 кг, цвет натуральный дуб."),
]


def load_prompt(vertical: str) -> str:
    path = PROMPTS / "examples" / (vertical + ".md")
    return path.read_text(encoding="utf-8")


def call_llm(system: str, facts: str, backend: str, ollama_model: str = OLLAMA_WRITER) -> str:
    user = "Ввод: %s\n\nФлаг: seo_required=true.\n\nВерни только JSON." % facts
    if backend == "ollama":
        response = requests.post(
            OLLAMA_BASE.rstrip("/") + "/api/chat",
            json={
                "model": ollama_model,
                "stream": False,
                "format": "json",  # жёсткий JSON-режим Ollama — без него qwen2.5 ломает разметку
                "options": {"num_ctx": OLLAMA_NUM_CTX, "temperature": 0.7},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=900,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    response = requests.post(
        BASE.rstrip("/") + "/chat/completions",
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # частая ошибка модели: запятая перед закрывающей скобкой
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(text)


def validate(obj: dict) -> list[str]:
    problems = []
    html = obj.get("description_html", "")
    if not html:
        return ["нет description_html"]
    if "Основные характеристики" not in html:
        problems.append("нет секции «Основные характеристики»")
    if html.count("faq-item") < 4:
        problems.append("мало faq-item")
    if not obj.get("summary_text"):
        problems.append("нет summary_text")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(FACTS))
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--backend", choices=["deepseek", "ollama"], default="deepseek")
    parser.add_argument("--ollama-model", default=OLLAMA_WRITER,
                        help="модель Ollama (по умолчанию из OLLAMA_WRITER_MODEL)")
    args = parser.parse_args()

    if args.backend == "deepseek" and not KEY:
        print("Нет LLM_API_KEY (ни в окружении, ни в %s). Попробуйте --backend ollama" % PARENT_ENV)
        return 2

    facts = FACTS[args.start: args.start + args.limit]
    OUT.parent.mkdir(parents=True, exist_ok=True)

    ok = fail = 0
    with OUT.open("w", encoding="utf-8") as handle:
        for vertical, fact in facts:
            obj = None
            last_error = ""
            for attempt in range(3):
                try:
                    hint = "" if attempt == 0 else (
                        "\n\nТвой предыдущий ответ не был валидным JSON. "
                        "Верни СТРОГО валидный JSON без markdown-обёрток."
                    )
                    raw = call_llm(load_prompt(vertical), fact + hint, args.backend,
                                   args.ollama_model)
                    obj = parse_json(raw)
                    break
                except Exception as error:  # noqa: BLE001
                    last_error = str(error)[:120]
            if obj is None:
                print("  !  %-11s JSON не вышел: %s" % (vertical, last_error))
                fail += 1
                continue
            try:
                problems = validate(obj)
                if problems:
                    print("  ! %-11s пропущено: %s" % (vertical, ", ".join(problems)))
                    fail += 1
                    continue
                name = re.sub(r"^Ткань для столового белья |^Ткань портьерная |^Ткань костюмная |^Ткань медицинская ", "", fact.split(",")[0])
                row = {
                    "vertical": vertical,
                    "facts": fact,
                    "description_html": obj["description_html"],
                    "summary_text": obj["summary_text"],
                    "meta_title": obj.get("meta_title"),
                    "meta_description": obj.get("meta_description"),
                    "model": args.ollama_model if args.backend == "ollama" else MODEL,
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                ok += 1
                print("  ok  %-11s %s" % (vertical, name[:48]))
            except Exception as error:  # noqa: BLE001
                print("  !  %-11s ошибка: %s" % (vertical, str(error)[:120]))
                fail += 1
            time.sleep(1)

    print("\nготово: %d сгенерировано, %d пропущено → %s" % (ok, fail, OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
