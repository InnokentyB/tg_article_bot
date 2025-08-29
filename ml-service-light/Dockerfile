# Легкий ML Service с внешними API
FROM python:3.11-alpine

# Устанавливаем только необходимые зависимости
RUN apk add --no-cache \
    wget \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Копируем легкие зависимости
COPY requirements-light.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY ml_server.py .

# Создаем пользователя
RUN adduser -D -s /bin/sh ml_user && \
    chown -R ml_user:ml_user /app
USER ml_user

EXPOSE 8000

CMD ["python", "ml_server.py"]
