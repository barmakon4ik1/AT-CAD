# CLAUDE.md — Вводный инструктаж по проекту AT-CAD

> Этот файл предназначен для ИИ-ассистента (Claude и др.).
> Читай его в начале каждой сессии, чтобы быстро войти в контекст проекта.

---

## 🧭 Что такое AT-CAD

**AT-CAD** — десктопное Python-приложение для автоматизации построения графических примитивов
в **AutoCAD**. Ориентировано на производство **сосудов, работающих под давлением**
из тонкостенного листового металла.

Автор: **А. Тутубалин** © 2025  
Язык интерфейса: **RU / EN / DE** (переключается в рантайме)  
Требует: запущенного AutoCAD на Windows

---

## ⚙️ Технологический стек

| Назначение        | Библиотека/технология              |
|-------------------|------------------------------------|
| GUI               | **wxPython**                       |
| AutoCAD bridge    | **pywin32** (COM), LISP-мост       |
| ORM / БД          | **peewee** + SQLite (.db файлы)    |
| Математика        | **pandas**, **matplotlib**         |
| Справочник        | **Django** (engineering_handbook)  |
| Документация      | **Sphinx** + sphinx_rtd_theme      |
| Точка входа       | `launcher.py` → `ATMainWindow`     |

---

## 📁 Структура проекта

```
AT-CAD/
├── launcher.py                  # Точка входа. Запускает ATMainWindow
├── requirements.txt
│
├── windows/                     # GUI-слой (wxPython)
│   ├── at_main_window.py        # Главное окно приложения ← ЦЕНТРАЛЬНЫЙ ФАЙЛ
│   ├── at_content_registry.py   # Реестр всех модулей (CONTENT_REGISTRY)
│   ├── at_window_utils.py       # Утилиты GUI (кнопки, шрифты, позиции)
│   ├── at_gui_utils.py          # Попапы, диалоги
│   ├── at_run_dialog_window.py  # Запуск контента
│   ├── at_settings_window.py    # Окно настроек
│   ├── at_service_panel.py      # Сервисная панель
│   ├── at_fields_builder.py     # Построитель полей ввода
│   ├── at_style.py              # Стили и цвета
│   ├── at_status_bar.py         # Строка статуса
│   ├── at_entity_inspector.py   # Инспектор объектов AutoCAD
│   ├── content_cone.py          # UI: конус прямой
│   ├── content_eccentric.py     # UI: конус эксцентрический
│   ├── content_shell.py         # UI: обечайка (цилиндр)
│   ├── content_nozzle.py        # UI: отвод/тройник
│   ├── content_head.py          # UI: днище
│   ├── content_plate.py         # UI: листовые заготовки
│   ├── content_cutout.py        # UI: вырез
│   ├── content_rings.py         # UI: кольца
│   ├── content_bracket.py       # UI: мостики для табличек
│   ├── content_cone_pipe.py     # UI: конусный отвод
│   ├── content_apps.py          # UI: приложения
│   ├── nameplate_dialog.py      # Диалог: шильдик
│   ├── slotted_hole_dialog.py   # Диалог: овальное отверстие
│   └── cone_offset_dialog.py    # Диалог: смещение конуса
│
├── programs/                    # Бизнес-логика и построение в AutoCAD
│   ├── at_base.py               # Базовый класс программ
│   ├── at_geometry.py           # Геометрические вычисления ← КЛЮЧЕВОЙ
│   ├── at_construction.py       # Построение примитивов в AutoCAD
│   ├── at_cylinder.py           # Обечайка: развёртка
│   ├── at_run_cone.py           # Конус: развёртка
│   ├── at_run_ecc_red.py        # Эксцентрический конус: развёртка
│   ├── at_nozzle.py             # Отвод: развёртка
│   ├── at_nozzle_cone.py        # Конусный отвод
│   ├── at_addhead.py            # Профиль днища
│   ├── at_run_plate.py          # Листовые заготовки
│   ├── at_cutout.py             # Вырез
│   ├── at_cutting.py            # Раскрой
│   ├── at_ringe.py              # Кольца
│   ├── at_packing.py            # Упаковка / компоновка
│   ├── at_name_plate.py         # Шильдик оборудования
│   ├── at_dimension.py          # Простановка размеров
│   ├── at_input.py              # Обработка пользовательского ввода
│   ├── at_calculation.py        # Вычисления
│   ├── at_data_manager.py       # Менеджер данных
│   └── lisp_bridge.py           # Python ↔ AutoCAD LISP мост
│
├── config/                      # Конфигурация
│   ├── at_config.py             # Константы: пути, размеры окон, иконки
│   ├── at_cad_init.py           # Инициализация CAD-соединения
│   ├── at_last_input.py         # Запоминание последнего ввода
│   ├── config.json              # Конфиг днищ: типы, формулы, таблицы h1
│   ├── common_data.json         # Общие данные (диаметры и т.д.)
│   ├── last_input.json          # Последний ввод пользователя
│   ├── last_position.json       # Последняя позиция окна
│   └── user_settings.json       # Пользовательские настройки
│
├── locales/                     # Локализация
│   ├── at_translations.py       # Главный объект `loc` с переводами
│   ├── at_localization.py       # Все строки переводов RU/EN/DE
│   ├── at_localization_class.py # Класс локализатора
│   └── at_localitation_manager.py
│
├── data/                        # Базы данных стандартов
│   ├── en1092-1.db              # Фланцы по EN 1092-1 (SQLite)
│   ├── AME_B16_5.db             # Фланцы по ASME B16.5 (SQLite, в разработке)
│   └── get_flange_en1092_1.py   # Запросы к БД фланцев
│
├── lisp_bridge/                 # LISP-мост к AutoCAD
│   ├── atc_bridge.lsp           # LISP-скрипт для AutoCAD
│   ├── atc_bridge_loader.lsp    # Загрузчик LISP
│   └── request.json             # Структура запроса
│
├── engineering_handbook/        # Django-справочник инженера
│   └── engineering_handbook.sqlite3
│
├── utils/                       # Вспомогательные утилиты
│   ├── alt_kfinder_gui.py       # GUI для поиска K-фактора
│   ├── cad_transaction.py       # Транзакции AutoCAD
│   ├── DXF.py                   # Работа с DXF
│   └── kfinder/                 # Утилита K-finder
│
├── errors/
│   └── at_errors.py             # Кастомные исключения
│
├── images/                      # Иконки и изображения UI
├── font/                        # Шрифты (BUSE letters)
└── docs/                        # Sphinx-документация
```

---

## 🔑 Ключевые паттерны

### Добавление нового модуля (content)
1. Создать `windows/content_<name>.py` — UI-панель (wxPanel)
2. Создать `programs/at_run_<name>.py` — логика построения в AutoCAD
3. Зарегистрировать в `windows/at_content_registry.py` → `CONTENT_REGISTRY`
4. Добавить переводы в `TRANSLATIONS` того же файла и в `locales/at_localization.py`

### Локализация
- Все строки хранятся в словарях `TRANSLATIONS` внутри каждого модуля
- Регистрируются через `loc.register_translations(TRANSLATIONS)`
- Получаются через `loc.get("ключ")`
- Языки: `"ru"`, `"en"`, `"de"`

### Связь с AutoCAD
- Через **pywin32** COM-объект
- Через **LISP-мост** (`lisp_bridge/`) — для операций, проще реализуемых на LISP
- Всегда требует запущенного AutoCAD

### Стандарты (БД)
- **EN 1092-1** — фланцы (реализовано)
- **ASME B16.5** — фланцы (в разработке)
- **DIN 28011 / 28013** — днища (реализовано через config.json)
- **ASME VIII-1 / NFE 81-103** — днища (реализовано через config.json)

---

## 🚧 Статус разработки (на момент создания файла)

- ✅ Конус прямой, эксцентрический
- ✅ Обечайка с вырезами и гравировкой
- ✅ Отвод, вырез, кольца, днища, листы
- ✅ Мостики для табличек (шильдики)
- ✅ БД фланцев EN 1092-1
- 🔄 БД фланцев ASME B16.5 (в процессе)
- 🔄 Engineering handbook (Django, в процессе)
- 💡 Много идей у автора — проект активно развивается

---

## 💬 Стиль работы с автором

- Автор: русскоязычный инженер-практик
- Общаться на **русском языке**
- Код комментировать на **русском**
- Автор сам решает приоритеты; задачи формулируются по ходу работы
- При предложении изменений — объяснять кратко и по существу
