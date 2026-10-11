import os
import logging
import json
import numpy as np
from typing import Dict, Any, Union
from openai import OpenAI, BadRequestError
import re
import logging
from pathlib import Path

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DentalAI")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_FILENAMES = ("best.pt", "dental_classifier.pt", "dental_yolo.pt")


def resolve_yolo_model_path() -> Path:
    """Find local dental weights without requiring a machine-specific path."""
    configured = os.getenv("YOLO_MODEL_PATH")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.is_file():
            return path.resolve()
        raise FileNotFoundError(f"YOLO_MODEL_PATH указывает на отсутствующий файл: {path}")

    model_dir = os.getenv("DENTALHELPER_MODEL_DIR")
    candidates = [
        PROJECT_ROOT / "weights" / "best.pt",
        PROJECT_ROOT / "models" / "best.pt",
        PROJECT_ROOT / "yolo_models" / "dental_classifier5" / "weights" / "best.pt",
        PROJECT_ROOT / "agent" / "models" / "best.pt",
    ]
    if model_dir:
        candidates.extend(Path(model_dir).expanduser() / filename for filename in MODEL_FILENAMES)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    expected = "weights/best.pt, models/best.pt или yolo_models/dental_classifier5/weights/best.pt"
    raise FileNotFoundError(
        "Не найдены веса стоматологической YOLO-модели. "
        f"Поместите файл в {expected} или укажите YOLO_MODEL_PATH в .env."
    )

def sanitize_input(value: Any) -> str:
    """Очистка входных данных от некорректных типов"""
    if value is None:
        return "неизвестно"
    if isinstance(value, (np.float32, np.float64)):
        return f"{float(value):.4f}"
    if isinstance(value, (np.int32, np.int64)):
        return str(int(value))
    if isinstance(value, dict):
        try:
            return json.dumps({str(k): sanitize_input(v) for k, v in value.items()}, ensure_ascii=False)
        except:
            return str(value)
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value).strip()

class DentalYOLOClassifier:
    """Классификатор зубов на основе YOLO"""
    def __init__(self):
        self.model_path = str(resolve_yolo_model_path())

        logger.info(f"Загрузка YOLO-модели из: {self.model_path}")

        self.device = os.getenv("YOLO_DEVICE", "cpu")
        self.model = None
        self.class_names = {}

        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path).to(self.device)
            self.class_names = self.model.names
            expected = {"calculus", "caries", "hypodontia", "mouth ulcer", "tooth discoloration", "healthy"}
            actual = {str(name).lower().replace("_", " ").strip() for name in self.class_names.values()}
            if self.model.task != "classify" or actual != expected:
                raise ValueError("Файл не является стоматологическим классификатором проекта с шестью классами.")
            logger.info(f"✅ YOLO-модель загружена! Классы: {list(self.class_names.values())}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки YOLO: {str(e)}")
            raise

    def predict(self, image_path: str) -> Dict[str, Any]:
        """Предсказание для изображения по пути"""
        if not os.path.exists(image_path):
            return {"error": f"Файл не найден: {image_path}"}

        try:
            results = self.model.predict(
                image_path,
                device=self.device,
                verbose=False,
                conf=0.25
            )

            if not results or len(results) == 0:
                return {"error": "Модель не вернула результатов"}

            probs = results[0].probs
            if probs is None:
                return {"error": "Не удалось получить вероятности классов"}

            top5_idx = probs.top5
            top5_conf = probs.top5conf

            # Преобразуем numpy типы в Python типы
            return {
                "diagnosis": str(self.class_names[top5_idx[0]]),
                "confidence": float(top5_conf[0]),
                "all_probabilities": {
                    str(self.class_names[idx]): float(conf)
                    for idx, conf in zip(top5_idx, top5_conf)
                }
            }
        except Exception as e:
            logger.exception(f"❌ Ошибка анализа: {str(e)}")
            return {"error": f"Ошибка анализа: {str(e)}"}

class DentalGemmaAgent:
    """Агент для генерации ответов с помощью Gemma3"""
    def __init__(self):
        self.ollama_client = OpenAI(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("OLLAMA_API_KEY", "ollama")
        )
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q5_K_M")
        logger.info(f"✅ Инициализирован Gemma агент с моделью: {self.model_name}")

    def clean_response(self, text: str) -> str:
        """
        Полная очистка ответа от форматирования и служебных тегов
        """
        if not text:
            return text

        # 1. Удаляем ВСЕ виды форматирования
        text = re.sub(r'[*_~`#]{1,3}', '', text)

        # 2. Удаляем служебные теги модели (конец ответа)
        text = re.sub(r'&lt;endofturn&gt;|<endofturn>|&lt;|&gt;', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)  # Удаляем все HTML-теги

        # 3. Удаляем строки с датой/пациентом
        patterns = [
            r'(?i)дата[:\s\.\[\]—–-].*?(?=\n|$)',
            r'(?i)patient[:\s\.\[\]—–-].*?(?=\n|$)',
            r'(?i)пациент[:\s\.\[\]—–-].*?(?=\n|$)',
            r'(?i)имя пациента[:\s\.\[\]—–-].*?(?=\n|$)',
            r'(?i)name[:\s\.\[\]—–-].*?(?=\n|$)',
            r'(?i)date[:\s\.\[\]—–-].*?(?=\n|$)',
            r'(?i)\[дата анализа\]',
            r'(?i)\[имя пациента\]',
        ]

        for pattern in patterns:
            text = re.sub(pattern, '', text)

        # 4. Удаляем лишние пустые строки
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 5. Убираем лишние пробелы
        lines = [re.sub(r'\s+', ' ', line.strip()) for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        # 6. Удаляем оставшиеся артефакты
        text = re.sub(r'(?i)^\s*(результаты анализа|заключение|анализ|отчет)[:\s]*$', '', text, flags=re.MULTILINE)

        # 7. Экранируем только критичные символы
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        return text.strip()

    def _safe_api_call(self, messages: list, max_retries=3) -> str:
        """Безопасный вызов API с повторными попытками и обработкой ошибок"""
        for attempt in range(max_retries):
            try:
                logger.debug(f"API запрос (попытка {attempt + 1}/{max_retries}):")
                for msg in messages:
                    logger.debug(f"  {msg['role']}: {msg['content'][:100]}...")

                response = self.ollama_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=512
                )

                if not response or not response.choices or not response.choices[0].message:
                    raise ValueError("Пустой ответ от API")

                answer = response.choices[0].message.content

                if not answer or len(answer.strip()) < 5:
                    raise ValueError("Слишком короткий ответ от API")

                logger.debug(f"API ответ (первые 150 символов): {answer[:150]}...")
                return answer

            except BadRequestError as e:
                error_detail = str(e)
                logger.error(f"❌ Ошибка API (попытка {attempt + 1}): {error_detail}")

                if "invalid message content type: <nil>" in error_detail:
                    logger.warning("⚠️ Обнаружена ошибка пустого контента")
                    for i, msg in enumerate(messages):
                        if not msg.get('content') or msg['content'].strip() == '':
                            logger.error(f"❌ Пустое сообщение в позиции {i}: {msg}")
                            return "❌ Ошибка: обнаружено пустое сообщение в запросе."

                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                else:
                    logger.error("❌ Все попытки API-запроса неудачны")
                    return "❌ Не удалось получить ответ от нейросети. Попробуйте позже."

            except Exception as e:
                logger.exception(f"❌ Неожиданная ошибка API (попытка {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                else:
                    return "❌ Критическая ошибка при обращении к нейросети."

    def answer_question(self, question: str) -> str:
        """Ответ на текстовый вопрос о стоматологии"""
        if not question or len(question.strip()) < 3:
            return "❌ Вопрос слишком короткий. Пожалуйста, задайте более подробный вопрос."

        cleaned_question = sanitize_input(question)

        messages = [
            {
                "role": "system",
                "content": (
                    "Ты — стоматолог-консультант с 10-летним опытом. "
                    "Отвечай простым текстом БЕЗ форматирования (без звездочек **, решеток ##, подчеркиваний __). "
                    "НЕ указывай дату, имя пациента или другие персональные данные. "
                    "ВСЕГДА добавляй предупреждение: 'Это не замена консультации с врачом-стоматологом.'"
                )
            },
            {
                "role": "user",
                "content": cleaned_question
            }
        ]

        raw_answer = self._safe_api_call(messages)
        return self.clean_response(raw_answer)

    def generate_report(self, yolo_result: dict) -> str:
        """Генерация отчета на основе результатов YOLO"""
        if not yolo_result:
            return "❌ Отсутствуют данные для анализа."

        if "error" in yolo_result:
            return f"❌ {sanitize_input(yolo_result['error'])}"

        try:
            diagnosis = sanitize_input(yolo_result.get('diagnosis', 'неизвестно'))
            confidence = sanitize_input(yolo_result.get('confidence', 0.0))
            probabilities = sanitize_input(yolo_result.get('all_probabilities', {}))

            prompt = (
                f"Проанализируй результат классификации стоматологического изображения:\n"
                f"Диагноз: {diagnosis}\n"
                f"Уверенность: {confidence}\n"
                f"Детальные вероятности: {probabilities}\n\n"
                "Сформируй краткий профессиональный отчет для пациента:\n"
                "- Используй простой текст БЕЗ форматирования (без **, ##, __)\n"
                "- НЕ указывай дату, имя пациента или другие персональные данные\n"
                "- Дай 2-3 рекомендации по уходу\n"
                "- В конце добавь: 'Это не замена консультации с врачом-стоматологом.'"
            )

            logger.info(f"Сформирован prompt для отчета (первые 100 символов): {prompt[:100]}...")

            if len(prompt.strip()) < 20:
                return "❌ Слишком короткий запрос для генерации отчета."

            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: добавлен вызов _safe_api_call
            raw_report = self._safe_api_call([{"role": "user", "content": prompt}])

            # Очищаем ответ
            cleaned_report = self.clean_response(raw_report)

            # Если после очистки текст слишком короткий — возвращаем оригинальный (но очищенный от опасных символов)
            if len(cleaned_report) < 20:
                cleaned_report = re.sub(r'[*_~`#]{2,}', '', raw_report)[:500]

            return cleaned_report

        except Exception as e:
            logger.exception(f"❌ Ошибка формирования отчета: {str(e)}")
            return "❌ Ошибка при подготовке данных для генерации отчета."
