# ML Service с тяжелыми моделями
FROM python:3.11-slim

# Устанавливаем системные зависимости для ML
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем ML зависимости
COPY ml-requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ML код
COPY ml_service/ .

# Создаем пользователя
RUN useradd --create-home --shell /bin/bash ml_user \
    && chown -R ml_user:ml_user /app
USER ml_user

EXPOSE 8000

CMD ["python", "ml_server.py"]
