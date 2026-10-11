# test_healthy.py
from ultralytics import YOLO

model = YOLO("E:/DentBot/yolo_models/dental_classifier5/weights/best.pt")

# Проверяем количество классов
print(f"Количество классов: {len(model.names)}")
print("Классы:", model.names)

# Тест на изображении
results = model.predict("E:/DentBot/pnggg/tye.jpg", device="cpu")
for r in results:
    print(f"\nДиагноз: {model.names[r.probs.top1]} ({r.probs.top1conf:.2%})")
    print("Топ-3 вероятности:")
    for i in range(3):
        idx = r.probs.top5[i]
        conf = r.probs.top5conf[i]
        print(f"  {i+1}. {model.names[idx]:20s} {conf:6.2%}")