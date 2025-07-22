import os


def replace_log_level(directory):
    for root, dirs, files in os.walk(directory):
        # Исключаем папку .venv
        if '.venv' in dirs:
            dirs.remove('.venv')  # Удаляем .venv из списка директорий для обхода
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    new_content = content.replace('logging.ERROR', 'logging.ERROR')
                    if new_content != content:  # Записываем только если были изменения
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Updated {file_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

# Укажите путь к проекту
replace_log_level(r'E:\AT-CAD')
