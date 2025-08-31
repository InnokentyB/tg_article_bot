FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY ml_server.py .

# Создание директории для моделей
RUN mkdir -p models

# Открытие порта
EXPOSE 8001

# Запуск сервиса
CMD ["python", "ml_server.py"]
