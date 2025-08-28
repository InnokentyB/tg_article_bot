# 🚀 Инструкции по развертыванию

## 🎯 Выбор платформы

### Для быстрого старта (рекомендуется):
- **Railway** - самый простой способ
- **Render** - хорошая альтернатива

### Для production:
- **VPS** - полный контроль
- **DigitalOcean App Platform** - профессиональное решение

---

## 🚂 Railway (Рекомендуется для начала)

### 1. Подготовка

1. Зарегистрируйтесь на [Railway.app](https://railway.app)
2. Подключите ваш GitLab репозиторий
3. Создайте новый проект

### 2. Настройка переменных окружения

В Railway Dashboard добавьте переменные:

```bash
DATABASE_URL=postgresql://article_bot:password@host:port/db
REDIS_URL=redis://host:port/0
ARTICLE_BOT_TOKEN=8016496837:AAHw5dv5b5X_Ad4GKBqVqzEH8izdS0aUytY
OPENAI_API_KEY=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
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 3. Настройка CI/CD

В GitLab CI/CD Variables добавьте:

```bash
RAILWAY_TOKEN=your_railway_token
RAILWAY_SERVICE_ID=your_service_id
RAILWAY_DOMAIN=your-app.railway.app
```

### 4. Деплой

```bash
# Автоматический деплой при push в main
git push origin main

# Или ручной деплой через GitLab CI/CD
```

---

## 🎨 Render

### 1. Подготовка

1. Зарегистрируйтесь на [Render.com](https://render.com)
2. Подключите GitLab репозиторий
3. Создайте новый Web Service

### 2. Настройка сервиса

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python api_server.py`
- **Environment**: `Python 3.11`

### 3. Переменные окружения

```bash
DATABASE_URL=postgresql://article_bot:password@host:port/db
REDIS_URL=redis://host:port/0
ARTICLE_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 4. Настройка CI/CD

В GitLab CI/CD Variables:

```bash
RENDER_DEPLOY_HOOK=https://api.render.com/deploy/srv-xxx
RENDER_SERVICE_URL=https://your-app.onrender.com
```

---

## 🖥️ VPS (DigitalOcean, Linode, Vultr)

### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Установка Git
sudo apt install git -y
```

### 2. Клонирование проекта

```bash
cd /opt
sudo git clone https://gitlab.com/i.a.bodrov85/tg_article_bot.git
sudo chown -R $USER:$USER tg_article_bot
cd tg_article_bot
```

### 3. Настройка переменных окружения

```bash
cp env.example .env
nano .env
```

Добавьте ваши переменные:

```bash
DATABASE_URL=postgresql://article_bot:article_bot_password@localhost:5432/article_bot
REDIS_URL=redis://localhost:6379/0
ARTICLE_BOT_TOKEN=8016496837:AAHw5dv5b5X_Ad4GKBqVqzEH8izdS0aUytY
OPENAI_API_KEY=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
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 4. Запуск

```bash
# Запуск всех сервисов
./docker-start.sh

# Или вручную
docker-compose up -d
```

### 5. Настройка CI/CD

В GitLab CI/CD Variables:

```bash
SSH_PRIVATE_KEY=your_ssh_private_key
VPS_USER=your_vps_user
VPS_HOST=your_vps_ip
VPS_DOMAIN=your_domain.com
```

### 6. Настройка домена (опционально)

```bash
# Установка Nginx
sudo apt install nginx -y

# Создание конфигурации
sudo nano /etc/nginx/sites-available/tg-article-bot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активация сайта
sudo ln -s /etc/nginx/sites-available/tg-article-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔧 Настройка CI/CD в GitLab

### 1. Переменные окружения

В GitLab → Settings → CI/CD → Variables добавьте:

#### Для Railway:
```bash
RAILWAY_TOKEN=your_railway_token
RAILWAY_SERVICE_ID=your_service_id
RAILWAY_DOMAIN=your-app.railway.app
```

#### Для Render:
```bash
RENDER_DEPLOY_HOOK=https://api.render.com/deploy/srv-xxx
RENDER_SERVICE_URL=https://your-app.onrender.com
```

#### Для VPS:
```bash
SSH_PRIVATE_KEY=your_ssh_private_key
VPS_USER=your_vps_user
VPS_HOST=your_vps_ip
VPS_DOMAIN=your_domain.com
```

### 2. Настройка Runner (если нужно)

```bash
# Установка GitLab Runner
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
sudo apt-get install gitlab-runner

# Регистрация Runner
sudo gitlab-runner register
```

---

## 📊 Мониторинг

### Health Checks

```bash
# API Health
curl https://your-domain.com/api/health

# Статистика
curl https://your-domain.com/api/stats
```

### Логи

```bash
# Railway
railway logs

# Render
render logs

# VPS
docker-compose logs -f
```

### Резервное копирование (VPS)

```bash
# Автоматическое резервное копирование
crontab -e

# Добавить строку для ежедневного бэкапа
0 2 * * * /opt/tg_article_bot/backup.sh
```

---

## 🚨 Troubleshooting

### Проблемы с подключением к БД

```bash
# Проверка подключения
docker-compose exec postgres psql -U article_bot -d article_bot

# Проверка логов
docker-compose logs postgres
```

### Проблемы с API

```bash
# Проверка статуса
docker-compose ps

# Проверка логов
docker-compose logs api

# Проверка health check
curl http://localhost:5001/api/health
```

### Проблемы с ботом

```bash
# Проверка логов бота
docker-compose logs bot

# Перезапуск бота
docker-compose restart bot
```

---

## 📈 Масштабирование

### Railway/Render
- Автоматическое масштабирование
- Настройка в Dashboard

### VPS
```bash
# Горизонтальное масштабирование
docker-compose up -d --scale api=3

# Вертикальное масштабирование
# Увеличьте ресурсы VPS
```

---

## 🔒 Безопасность

### SSL/TLS
- Railway/Render: автоматически
- VPS: Let's Encrypt

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com
```

### Firewall
```bash
# Настройка UFW
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs`
2. Проверьте переменные окружения
3. Проверьте подключение к базе данных
4. Проверьте health checks

**Удачи с развертыванием!** 🚀
