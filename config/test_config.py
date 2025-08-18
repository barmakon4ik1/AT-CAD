import os
from at_config import *  # импорт всех переменных и настроек

# Цвета для консоли
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

def check_path(path, name=""):
    # Если путь относительный, добавляем BASE_DIR
    full_path = os.path.join(BASE_DIR, path) if not os.path.isabs(path) else path
    if os.path.exists(full_path):
        print(f"{GREEN}{name}: {full_path} (существует){RESET}")
    else:
        print(f"{RED}{name}: {full_path} (не найден){RESET}")

def main():
    print("=== Тестирование переменных at_config ===\n")

    # Проверяем основные директории и файлы
    check_path(BASE_DIR, "BASE_DIR")
    check_path(IMAGES_DIR, "IMAGES_DIR")
    check_path(RESOURCE_DIR, "RESOURCE_DIR")
    check_path(USER_CONFIG_PATH, "USER_CONFIG_PATH")
    check_path(USER_LANGUAGE_PATH, "USER_LANGUAGE_PATH")
    check_path(ICON_PATH, "ICON_PATH")
    check_path(RING_IMAGE_PATH, "RING_IMAGE_PATH")
    check_path(HEAD_IMAGE_PATH, "HEAD_IMAGE_PATH")
    check_path(PLATE_IMAGE_PATH, "PLATE_IMAGE_PATH")
    check_path(CONE_IMAGE_PATH, "CONE_IMAGE_PATH")
    check_path(DONE_ICON_PATH, "DONE_ICON_PATH")
    check_path(LAST_CONE_INPUT_FILE, "LAST_CONE_INPUT_FILE")

    # Языковые иконки
    print("\nLANGUAGE_ICONS:")
    for lang, path in LANGUAGE_ICONS.items():
        check_path(path, lang)

    # Меню иконки
    print("\nMENU_ICONS:")
    for name, path in MENU_ICONS.items():
        check_path(path, name)

    # Настройки (проверяем наличие значений)
    print("\nDEFAULT_SETTINGS:")
    for key, value in DEFAULT_SETTINGS.items():
        exists = value is not None
        color = GREEN if exists else RED
        print(f"{color}{key}: {value}{RESET}")

if __name__ == "__main__":
    main()
