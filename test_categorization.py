#!/usr/bin/env python3
"""
Тест улучшенной категоризации
"""
import random

def test_categorization():
    """Тестируем улучшенную категоризацию"""
    print("🏷️ Тестирование улучшенной категоризации...")
    
    # Define categories and their keywords
    categories = {
        'Технологии': ['tech', 'programming', 'ai', 'machine', 'software', 'hardware', 'computer', 'digital', 'internet', 'web', 'app', 'mobile', 'cloud', 'data', 'algorithm'],
        'Наука': ['science', 'research', 'study', 'experiment', 'discovery', 'theory', 'physics', 'chemistry', 'biology', 'medicine', 'health', 'medical', 'clinical', 'laboratory'],
        'Бизнес': ['business', 'company', 'market', 'finance', 'economy', 'investment', 'startup', 'entrepreneur', 'management', 'strategy', 'profit', 'revenue', 'growth'],
        'Образование': ['education', 'learning', 'school', 'university', 'course', 'training', 'student', 'teacher', 'academic', 'knowledge', 'study', 'research'],
        'Медицина': ['health', 'medical', 'doctor', 'hospital', 'treatment', 'disease', 'patient', 'medicine', 'therapy', 'surgery', 'diagnosis', 'prevention'],
        'Финансы': ['finance', 'money', 'banking', 'investment', 'trading', 'stock', 'market', 'economy', 'currency', 'crypto', 'bitcoin', 'trading']
    }
    
    # Test URLs
    test_urls = [
        "https://techcrunch.com/ai-machine-learning-article",
        "https://science.org/research-medical-discovery",
        "https://business.com/startup-investment-strategy",
        "https://education.edu/learning-course-training",
        "https://health.com/medical-treatment-therapy",
        "https://finance.com/crypto-bitcoin-trading",
        "https://example.com/random-article",
        "https://tech.com/science-research-ai",
        "https://business.com/finance-investment-market"
    ]
    
    print("\n🔍 Тестирование категоризации по URL:")
    
    for url in test_urls:
        url_lower = url.lower()
        detected_categories = []
        
        for category, keywords in categories.items():
            if any(keyword in url_lower for keyword in keywords):
                detected_categories.append(category)
        
        # If no categories detected, use default
        if not detected_categories:
            detected_categories = ['Технологии']
        
        # Primary category is the first one
        primary_category = detected_categories[0]
        
        # Format categories for display
        if len(detected_categories) > 1:
            categories_text = f"🏷️ Основная: {primary_category} | Все: {', '.join(detected_categories)}"
        else:
            categories_text = f"🏷️ {primary_category}"
        
        print(f"   {url}")
        print(f"   {categories_text}")
        print()
    
    print("✅ Тест завершен!")

def show_categories():
    """Показываем доступные категории"""
    print("\n📋 Доступные категории:")
    
    categories = {
        'Технологии': ['tech', 'programming', 'ai', 'machine', 'software', 'hardware', 'computer', 'digital', 'internet', 'web', 'app', 'mobile', 'cloud', 'data', 'algorithm'],
        'Наука': ['science', 'research', 'study', 'experiment', 'discovery', 'theory', 'physics', 'chemistry', 'biology', 'medicine', 'health', 'medical', 'clinical', 'laboratory'],
        'Бизнес': ['business', 'company', 'market', 'finance', 'economy', 'investment', 'startup', 'entrepreneur', 'management', 'strategy', 'profit', 'revenue', 'growth'],
        'Образование': ['education', 'learning', 'school', 'university', 'course', 'training', 'student', 'teacher', 'academic', 'knowledge', 'study', 'research'],
        'Медицина': ['health', 'medical', 'doctor', 'hospital', 'treatment', 'disease', 'patient', 'medicine', 'therapy', 'surgery', 'diagnosis', 'prevention'],
        'Финансы': ['finance', 'money', 'banking', 'investment', 'trading', 'stock', 'market', 'economy', 'currency', 'crypto', 'bitcoin', 'trading']
    }
    
    for category, keywords in categories.items():
        print(f"   🏷️ {category}: {', '.join(keywords[:5])}...")

def main():
    """Основная функция"""
    print("🧪 Тестирование улучшенной категоризации\n")
    
    show_categories()
    test_categorization()
    
    print("\n📝 Примеры URL для тестирования:")
    print("   • https://techcrunch.com/ai-article → Технологии")
    print("   • https://science.org/research → Наука")
    print("   • https://business.com/startup → Бизнес")
    print("   • https://health.com/medical → Медицина")
    print("   • https://finance.com/crypto → Финансы")
    print("   • https://tech.com/science-ai → Технологии, Наука")

if __name__ == "__main__":
    main()
