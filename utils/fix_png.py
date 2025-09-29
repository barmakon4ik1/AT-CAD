import os
from PIL import Image

def clean_png_metadata(folder="images"):
    for file in os.listdir(folder):
        if file.lower().endswith(".png"):
            path = os.path.join(folder, file)
            try:
                img = Image.open(path)
                # сохраняем копию поверх исходного файла
                img.save(path, "PNG")
                print(f"[OK] очищен файл: {file}")
            except Exception as e:
                print(f"[Ошибка] {file}: {e}")

if __name__ == "__main__":
    clean_png_metadata("../images")
