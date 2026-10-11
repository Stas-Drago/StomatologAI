import os
import shutil
import random
from pathlib import Path

# Настройки
SOURCE_DIR = "E:/DentBot/Tooth_dataset"
TARGET_DIR = "E:/DentBot/yolo_data"
# ВАЖНО: добавлен класс 'healthy' как 6-й элемент
CLASSES = ["Calculus", "caries", "hypodontia", "Mouth Ulcer", "Tooth Discoloration", "healthy"]
SPLIT_RATIO = (0.7, 0.2, 0.1)  # train, val, test

# Создание структуры (только для изображений)
for split in ["train", "val", "test"]:
    for cls in CLASSES:
        os.makedirs(f"{TARGET_DIR}/images/{split}/{cls}", exist_ok=True)

# Разделение данных
for cls in CLASSES:
    class_dir = Path(SOURCE_DIR) / cls
    if not class_dir.exists():
        print(f"⚠️ Класс '{cls}' не найден в {SOURCE_DIR}. Пропускаем...")
        continue

    images = [f for f in class_dir.iterdir()
              if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']]

    if not images:
        print(f"⚠️ Нет изображений для класса '{cls}'. Пропускаем...")
        continue

    random.shuffle(images)
    total = len(images)
    train_count = int(total * SPLIT_RATIO[0])
    val_count = int(total * SPLIT_RATIO[1])

    print(f"\n📊 Класс: {cls} | Всего: {total} изображений")
    print(f"   Train: {train_count}, Val: {val_count}, Test: {total - train_count - val_count}")

    for i, img_path in enumerate(images):
        split = "train" if i < train_count else "val" if i < train_count + val_count else "test"
        dst_path = Path(TARGET_DIR) / "images" / split / cls / img_path.name
        shutil.copy(img_path, dst_path)
        print(f"  ✓ {img_path.name} → {split}/{cls}")

print("\n✅ Разделение данных завершено!")