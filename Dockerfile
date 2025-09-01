# Многоэтапная сборка для production
FROM python:3.11-alpine AS builder

# Устанавливаем системные зависимости для сборки
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    libxml2-dev \
    libxslt-dev \
    jpeg-dev \
    zlib-dev \
    && rm -rf /var/cache/apk/*

# Создаем виртуальное окружение
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем и устанавливаем Python зависимости
COPY requirements.railway.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.railway.txt

# Финальный образ
FROM python:3.11-alpine AS runtime

# Устанавливаем только runtime зависимости
RUN apk add --no-cache \
    postgresql-libs \
    libxml2 \
    libxslt \
    jpeg \
    zlib \
    wget \
    && rm -rf /var/cache/apk/*

# Копируем виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем основные файлы API сервера
COPY --chown=nobody:nobody api_server.py .
COPY --chown=nobody:nobody database.py .
COPY --chown=nobody:nobody text_extractor.py .
COPY --chown=nobody:nobody requirements.railway.txt .
COPY --chown=nobody:nobody init.sql .

# Создаем пользователя для безопасности
RUN adduser -D -s /bin/sh app && \
    chown -R app:app /app
USER app

# Открываем порт
EXPOSE 5000

# Команда по умолчанию
CMD ["python", "api_server.py"]
