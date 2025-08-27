"""
BART-based zero-shot classification for article categorization
Alternative categorization approach using transformers
"""
import logging
from typing import List, Dict, Tuple
import re

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Rule-based categorization as fallback
CATEGORY_RULES = {
    "Системный анализ / Инженерия": {
        "keywords": ["системный анализ", "системный аналитик", "uml", "bpmn", "техническое задание", 
                    "требования", "анализ требований", "проектирование систем"],
        "weight": 1.0
    },
    "HR / Рынок труда IT": {
        "keywords": ["вакансии", "работа", "карьера", "собеседование", "рынок труда", "зарплаты", 
                    "hr", "рекрутинг", "резюме", "поиск работы", "трудоустройство"],
        "weight": 1.0
    },
    "Инструменты и технологии": {
        "keywords": ["python", "javascript", "react", "node.js", "frameworks", "библиотеки", 
                    "инструменты", "технологии", "ide", "разработка", "программирование"],
        "weight": 0.9
    },
    "Зарплаты и компенсации": {
        "keywords": ["зарплата", "оклад", "компенсации", "бонусы", "доходы", "заработок", 
                    "стоимость специалиста", "зарплатная вилка"],
        "weight": 0.9
    },
    "Профессиональные навыки": {
        "keywords": ["навыки", "компетенции", "обучение", "курсы", "сертификация", 
                    "повышение квалификации", "развитие", "скиллы"],
        "weight": 0.8
    },
    "Архитектура и проектирование": {
        "keywords": ["архитектура", "проектирование", "паттерны", "ddd", "микросервисы", 
                    "design patterns", "системная архитектура"],
        "weight": 0.8
    },
    "Управление проектами": {
        "keywords": ["управление проектами", "менеджмент", "agile", "scrum", "kanban", 
                    "проектный менеджмент", "планирование"],
        "weight": 0.8
    },
    "Безопасность информации": {
        "keywords": ["безопасность", "security", "защита информации", "криптография", 
                    "кибербезопасность", "уязвимости"],
        "weight": 0.8
    },
    "Образование и обучение": {
        "keywords": ["образование", "обучение", "университет", "курсы", "образовательные программы", 
                    "студенты", "преподавание"],
        "weight": 0.7
    },
    "Бизнес и финансы": {
        "keywords": ["бизнес", "финансы", "стартап", "инвестиции", "налоги", "налогообложение", 
                    "эмиграция", "резидентство", "фнс", "ндфл", "предпринимательство"],
        "weight": 0.8
    }
}

logger = logging.getLogger(__name__)

class BartCategorizer:
    """
    Zero-shot classification using BART model
    Provides categorical classification with confidence scores
    """
    
    def __init__(self):
        """Initialize BART categorizer"""
        self.classifier = None
        self.candidate_labels = [
            "Системный анализ / Инженерия",
            "HR / Рынок труда IT", 
            "Инструменты и технологии",
            "Зарплаты и компенсации",
            "Профессиональные навыки",
            "Архитектура и проектирование",
            "Управление проектами",
            "Безопасность информации",
            "Образование и обучение",
            "Бизнес и финансы"
        ]
        
        if TRANSFORMERS_AVAILABLE:
            try:
                logger.info("Initializing BART classifier...")
                self.classifier = pipeline(
                    "zero-shot-classification", 
                    model="facebook/bart-large-mnli"
                )
                logger.info("BART classifier initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize BART classifier: {e}")
                self.classifier = None
        else:
            logger.warning("Transformers not available, BART classifier disabled")
    
    def is_available(self) -> bool:
        """Check if BART classifier is available"""
        return self.classifier is not None
    
    def _clean_text(self, text: str) -> str:
        """Clean text for processing"""
        if not text:
            return ""
        
        # Remove URLs, special characters, and normalize whitespace
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'[^\w\s\-.,!?;:]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def categorize_article(self, text: str, title: str = "") -> Dict:
        """
        Categorize article using BART zero-shot classification or rule-based fallback
        
        Args:
            text: Article text
            title: Article title (optional)
            
        Returns:
            Dict with classification results
        """
        try:
            # Prepare text
            full_text = f"{title} {text}" if title else text
            clean_text = self._clean_text(full_text)
            
            if len(clean_text) < 50:
                return {
                    "primary_category": "Слишком короткий текст",
                    "categories": [],
                    "confidence": 0.0,
                    "method": "text_too_short"
                }
            
            # Try BART if available
            if self.is_available():
                # Limit text length for BART (max ~1000 tokens)
                if len(clean_text) > 4000:
                    clean_text = clean_text[:4000] + "..."
                
                # Perform zero-shot classification
                result = self.classifier(clean_text, self.candidate_labels, multi_label=True)
                
                # Extract results
                categories_with_scores = list(zip(result['labels'], result['scores']))
                
                # Get primary category (highest confidence)
                primary_category = categories_with_scores[0][0] if categories_with_scores else "Unknown"
                primary_confidence = categories_with_scores[0][1] if categories_with_scores else 0.0
                
                # Get top categories with confidence > 0.1
                top_categories = [
                    {"category": label, "confidence": score} 
                    for label, score in categories_with_scores 
                    if score > 0.1
                ][:3]  # Top 3
                
                return {
                    "primary_category": primary_category,
                    "categories": top_categories,
                    "confidence": primary_confidence,
                    "method": "bart_zero_shot",
                    "all_scores": categories_with_scores
                }
            else:
                # Use rule-based classification as fallback
                return self._rule_based_classification(clean_text)
            
        except Exception as e:
            logger.error(f"Error in BART categorization: {e}")
            # Fallback to rule-based on error
            try:
                return self._rule_based_classification(self._clean_text(f"{title} {text}"))
            except:
                return {
                    "primary_category": "Ошибка классификации",
                    "categories": [],
                    "confidence": 0.0,
                    "method": "error",
                    "error": str(e)
                }
    
    def _rule_based_classification(self, text: str) -> Dict:
        """Rule-based classification as fallback when BART is unavailable"""
        logger.info("   🔧 Запуск правило-ориентированной классификации...")
        text_lower = text.lower()
        
        category_scores = {}
        
        # Calculate scores for each category
        logger.info("   📊 Анализ по правилам для каждой категории...")
        for category, data in CATEGORY_RULES.items():
            score = 0
            matched_keywords = []
            
            for keyword in data["keywords"]:
                if keyword.lower() in text_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                # Normalize score
                normalized_score = min((score / len(data["keywords"])) * data["weight"], 0.95)
                category_scores[category] = {
                    "score": normalized_score,
                    "matched_keywords": matched_keywords
                }
        
        if not category_scores:
            logger.info("   ⚠️ Не найдено совпадений по правилам")
            return {
                "primary_category": "Общая тема",
                "categories": [],
                "confidence": 0.1,
                "method": "rule_based_fallback"
            }
        
        # Sort by score
        logger.info(f"   ✅ Найдено {len(category_scores)} подходящих категорий")
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        for i, (cat, data) in enumerate(sorted_categories[:3]):
            logger.info(f"   {i+1}. {cat}: {data['score']:.2%} (термины: {data['matched_keywords'][:3]})")
        
        primary_category = sorted_categories[0][0]
        primary_confidence = sorted_categories[0][1]["score"]
        
        # Build top categories
        top_categories = [
            {
                "category": cat,
                "confidence": data["score"],
                "matched_keywords": data["matched_keywords"]
            }
            for cat, data in sorted_categories[:3]
            if data["score"] > 0.05
        ]
        
        return {
            "primary_category": primary_category,
            "categories": top_categories,
            "confidence": primary_confidence,
            "method": "rule_based_classification",
            "matched_keywords": sorted_categories[0][1]["matched_keywords"]
        }
    
    def get_category_mapping(self) -> Dict[str, str]:
        """Get mapping of BART categories to system categories"""
        return {
            "Системный анализ / Инженерия": "Architecture",
            "HR / Рынок труда IT": "Career", 
            "Инструменты и технологии": "Programming",
            "Зарплаты и компенсации": "Career",
            "Профессиональные навыки": "Career",
            "Архитектура и проектирование": "Architecture",
            "Управление проектами": "Management",
            "Безопасность информации": "Security",
            "Образование и обучение": "Education",
            "Бизнес и финансы": "Business"
        }