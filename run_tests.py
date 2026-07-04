#!/usr/bin/env python3
"""
Скрипт для запуска автотестов
"""
import subprocess
import sys
import os

def run_tests():
    """Запуск тестов"""
    print("🧪 Запуск автотестов...")
    
    # Проверяем, что мы в правильной директории
    if not os.path.exists("tests/test_mvp_api.py"):
        print("❌ Файл tests/test_mvp_api.py не найден!")
        return False
    
    # Устанавливаем переменные окружения для тестов
    env = os.environ.copy()
    env.setdefault("API_BASE_URL", "http://localhost:5001")
    env.setdefault("API_KEY", "local-dev-key")
    
    try:
        # Запускаем тесты
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/test_mvp_api.py",
            "-v",
            "--tb=short"
        ], env=env, capture_output=True, text=True)
        
        print("📋 Результаты тестов:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Предупреждения:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Все тесты прошли успешно!")
            return True
        else:
            print("❌ Некоторые тесты не прошли!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при запуске тестов: {e}")
        return False

def run_specific_test(test_name):
    """Запуск конкретного теста"""
    print(f"🧪 Запуск теста: {test_name}")
    
    env = os.environ.copy()
    env.setdefault("API_BASE_URL", "http://localhost:5001")
    env.setdefault("API_KEY", "local-dev-key")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            f"tests/test_mvp_api.py::{test_name}",
            "-v",
            "--tb=short"
        ], env=env, capture_output=True, text=True)
        
        print("📋 Результат теста:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Предупреждения:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Ошибка при запуске теста: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Запуск конкретного теста
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # Запуск всех тестов
        success = run_tests()
    
    sys.exit(0 if success else 1)
