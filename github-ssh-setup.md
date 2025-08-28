# 🔑 Настройка SSH ключей для GitHub

## Шаг 1: Создание SSH ключа для GitHub

```bash
# Создайте новый SSH ключ для GitHub
ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/github_key

# Или используйте RSA (если ed25519 не поддерживается)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com" -f ~/.ssh/github_key
```

## Шаг 2: Добавление ключа в SSH агент

```bash
# Запустите SSH агент
eval "$(ssh-agent -s)"

# Добавьте ключ
ssh-add ~/.ssh/github_key
```

## Шаг 3: Настройка SSH конфигурации

Создайте или отредактируйте файл `~/.ssh/config`:

```bash
# Существующие настройки для GitLab
Host gitlab.com
  IdentityFile ~/.ssh/gitlab_key
  IdentitiesOnly yes

# Добавьте настройки для GitHub
Host github.com
  IdentityFile ~/.ssh/github_key
  IdentitiesOnly yes
```

## Шаг 4: Добавление публичного ключа в GitHub

```bash
# Скопируйте публичный ключ
cat ~/.ssh/github_key.pub
```

1. Перейдите на [GitHub.com](https://github.com)
2. Settings → SSH and GPG keys → New SSH key
3. Вставьте скопированный ключ
4. Назовите ключ (например, "GitLab CI")
5. Нажмите "Add SSH key"

## Шаг 5: Тестирование подключения

```bash
# Проверьте подключение к GitHub
ssh -T git@github.com
```

Вы должны увидеть: `Hi username! You've successfully authenticated...`

## Шаг 6: Настройка GitLab CI/CD

В GitLab → Settings → CI/CD → Variables добавьте:

### Переменная: `GITHUB_SSH_KEY`
- **Value**: Содержимое приватного ключа
```bash
cat ~/.ssh/github_key
```
- **Type**: Variable
- **Protected**: ✅
- **Masked**: ✅

### Переменная: `GITHUB_USERNAME`
- **Value**: Ваш GitHub username
- **Type**: Variable
- **Protected**: ❌
- **Masked**: ❌

## Шаг 7: Создание GitHub репозитория

1. Перейдите на [GitHub.com](https://github.com)
2. Создайте новый репозиторий: `tg_article_bot`
3. **НЕ** инициализируйте с README
4. Скопируйте URL: `https://github.com/YOUR_USERNAME/tg_article_bot.git`

## Шаг 8: Запуск скрипта настройки

```bash
# Запустите скрипт настройки
./setup-github-mirror.sh YOUR_GITHUB_USERNAME
```

## Шаг 9: Настройка Railway

1. Перейдите на [Railway.app](https://railway.app)
2. Создайте новый проект
3. Выберите "Deploy from GitHub repo"
4. Подключите ваш GitHub репозиторий
5. Настройте переменные окружения

## Переменные окружения для Railway

```bash
DATABASE_URL=postgresql://article_bot:password@host:port/db
REDIS_URL=redis://host:port/0
ARTICLE_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 🎯 Результат

После настройки:
- ✅ Код автоматически синхронизируется с GitHub
- ✅ Railway может подключиться к GitHub репозиторию
- ✅ Автоматические деплои при push в main
- ✅ Полная интеграция GitLab CI/CD с Railway

## 🔧 Troubleshooting

### Ошибка: Permission denied
```bash
# Проверьте права на ключ
chmod 600 ~/.ssh/github_key

# Проверьте SSH конфигурацию
ssh -T git@github.com -v
```

### Ошибка: Repository not found
- Убедитесь, что репозиторий создан на GitHub
- Проверьте правильность username
- Убедитесь, что у вас есть права на запись

### Ошибка: Authentication failed
- Проверьте, что публичный ключ добавлен в GitHub
- Убедитесь, что приватный ключ правильно добавлен в GitLab CI/CD
