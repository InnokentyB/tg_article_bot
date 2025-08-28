# 🔄 Настройка GitHub зеркала для Railway

## Способ 1: GitHub Mirror (Рекомендуется)

### 1. Создайте репозиторий на GitHub

1. Перейдите на [GitHub.com](https://github.com)
2. Создайте новый репозиторий: `tg_article_bot`
3. **НЕ** инициализируйте с README

### 2. Добавьте GitHub как remote

```bash
# Добавьте GitHub как дополнительный remote
git remote add github https://github.com/YOUR_USERNAME/tg_article_bot.git

# Или если у вас SSH ключ для GitHub
git remote add github git@github.com:YOUR_USERNAME/tg_article_bot.git
```

### 3. Настройте автоматическую синхронизацию

```bash
# Отправьте код на GitHub
git push github main

# Настройте автоматическую синхронизацию
git push github main --set-upstream
```

### 4. Настройте GitLab CI для автоматической синхронизации

Добавьте в `.gitlab-ci.yml`:

```yaml
sync_to_github:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache git openssh-client
    - eval $(ssh-agent -s)
    - echo "$GITHUB_SSH_KEY" | tr -d '\r' | ssh-add -
    - mkdir -p ~/.ssh
    - chmod 700 ~/.ssh
  script:
    - git remote add github git@github.com:YOUR_USERNAME/tg_article_bot.git || true
    - git push github main
  only:
    - main
  when: manual
```

### 5. Настройте переменные в GitLab CI/CD

В GitLab → Settings → CI/CD → Variables добавьте:
- `GITHUB_SSH_KEY` - ваш приватный SSH ключ для GitHub

---

## Способ 2: Прямое подключение GitLab (Через API)

### 1. Создайте Personal Access Token в GitLab

1. Перейдите в GitLab → Settings → Access Tokens
2. Создайте токен с правами `read_repository`
3. Скопируйте токен

### 2. Используйте Railway CLI

```bash
# Установите Railway CLI
npm install -g @railway/cli

# Войдите в Railway
railway login

# Создайте проект
railway init

# Подключите GitLab репозиторий
railway link --repo https://gitlab.com/i.a.bodrov85/tg_article_bot.git
```

### 3. Настройте переменные окружения

```bash
# В Railway Dashboard или через CLI
railway variables set DATABASE_URL="postgresql://..."
railway variables set REDIS_URL="redis://..."
railway variables set ARTICLE_BOT_TOKEN="your_telegram_bot_token_here"
railway variables set OPENAI_API_KEY="your_openai_api_key_here"
```

---

## Способ 3: Ручной деплой через Railway CLI

### 1. Установите Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Настройте проект

```bash
# Войдите в Railway
railway login

# Создайте новый проект
railway init

# Скопируйте файлы проекта
cp -r ./* /tmp/railway-project/
cd /tmp/railway-project/

# Деплой
railway up
```

---

## Способ 4: Альтернативные платформы

Если Railway не подходит, рассмотрите:

### Render.com
- ✅ Поддерживает GitLab напрямую
- ✅ Простая настройка
- ✅ Бесплатный tier

### Heroku
- ✅ Поддерживает GitLab
- ✅ Хорошая документация
- ✅ Множество аддонов

### DigitalOcean App Platform
- ✅ Поддерживает GitLab
- ✅ Профессиональное решение
- ✅ Хорошая производительность

---

## 🎯 Рекомендация

**Используйте Способ 1 (GitHub Mirror)** - это самый надежный и простой способ для Railway.
