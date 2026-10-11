from ultralytics import YOLO

model = YOLO("yolov8n-cls.pt")

results = model.train(
    data="E:/DentBot/yolo_data",
    epochs=50,
    batch=8,
    imgsz=224,
    device="cpu",
    workers=0,
    name="dental_classifier5",  # Новое имя для 6 классов
    project="E:/DentBot/yolo_models",
    patience=15,
    exist_ok=False  # Запрещаем перезапись существующей папки
)

# Экспорт модели
model.export(format='onnx', dynamic=True)
print("✅ Модель успешно обучена и экспортирована!")