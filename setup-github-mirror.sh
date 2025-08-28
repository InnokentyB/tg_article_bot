#!/bin/bash

# Скрипт для настройки GitHub зеркала для Railway
# Использование: ./setup-github-mirror.sh YOUR_GITHUB_USERNAME

set -e

GITHUB_USERNAME=${1:-""}

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ Ошибка: Укажите GitHub username"
    echo "Использование: ./setup-github-mirror.sh YOUR_GITHUB_USERNAME"
    exit 1
fi

echo "🔄 Настройка GitHub зеркала для Railway..."
echo "GitHub username: $GITHUB_USERNAME"

# Проверяем, что мы в Git репозитории
if [ ! -d ".git" ]; then
    echo "❌ Ошибка: Это не Git репозиторий"
    exit 1
fi

# Проверяем, что GitHub remote еще не добавлен
if git remote get-url github > /dev/null 2>&1; then
    echo "⚠️  GitHub remote уже добавлен"
    echo "Текущий URL: $(git remote get-url github)"
    read -p "Хотите обновить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Отменено"
        exit 0
    fi
    git remote remove github
fi

# Добавляем GitHub remote
echo "🔗 Добавление GitHub remote..."
git remote add github https://github.com/$GITHUB_USERNAME/tg_article_bot.git

# Проверяем подключение
echo "🔍 Проверка подключения к GitHub..."
if git ls-remote github > /dev/null 2>&1; then
    echo "✅ Подключение к GitHub успешно"
else
    echo "❌ Ошибка подключения к GitHub"
    echo "Убедитесь, что:"
    echo "1. Репозиторий создан на GitHub: https://github.com/$GITHUB_USERNAME/tg_article_bot"
    echo "2. У вас есть права на запись"
    exit 1
fi

# Отправляем код на GitHub
echo "📤 Отправка кода на GitHub..."
git push github main

# Настраиваем upstream
echo "🔧 Настройка upstream..."
git push github main --set-upstream

echo ""
echo "✅ GitHub зеркало настроено успешно!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Перейдите в GitLab → Settings → CI/CD → Variables"
echo "2. Добавьте переменную GITHUB_USERNAME = $GITHUB_USERNAME"
echo "3. Добавьте переменную GITHUB_SSH_KEY = ваш_приватный_ssh_ключ"
echo "4. В Railway подключите GitHub репозиторий"
echo "5. Настройте переменные окружения в Railway"
echo ""
echo "🔗 GitHub репозиторий: https://github.com/$GITHUB_USERNAME/tg_article_bot"
echo "🚂 Railway Dashboard: https://railway.app"
