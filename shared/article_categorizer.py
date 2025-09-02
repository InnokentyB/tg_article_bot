"""
Article categorization using simple keyword-based approach for MVP
"""
import logging
from typing import List, Optional
from langdetect import detect, DetectorFactory
from sklearn.feature_extraction.text import TfidfVectorizer
import re

logger = logging.getLogger(__name__)

# Set seed for consistent language detection
DetectorFactory.seed = 0

class ArticleCategorizer:
    def __init__(self):
        # Define category keywords (можно расширить)
        self.categories = {
            'технологии': [
                'технология', 'компьютер', 'программирование', 'код', 'разработка',
                'софтвер', 'приложение', 'сайт', 'интернет', 'цифровой', 'ИТ'
            ],
            'наука': [
                'исследование', 'наука', 'ученый', 'открытие', 'эксперимент',
                'физика', 'химия', 'биология', 'математика', 'медицина'
            ],
            'бизнес': [
                'бизнес', 'компания', 'стартап', 'инвестиции', 'экономика',
                'рынок', 'финансы', 'деньги', 'прибыль', 'продажи'
            ],
            'образование': [
                'образование', 'учеба', 'университет', 'школа', 'курс',
                'обучение', 'студент', 'преподаватель', 'знания'
            ],
            'спорт': [
                'спорт', 'футбол', 'хоккей', 'баскетбол', 'олимпиада',
                'тренировка', 'команда', 'матч', 'соревнование'
            ],
            'развлечения': [
                'кино', 'фильм', 'актер', 'музыка', 'игра', 'книга',
                'театр', 'концерт', 'шоу', 'телевидение'
            ]
        }
        
        # English categories
        self.categories_en = {
            'technology': [
                'technology', 'computer', 'programming', 'code', 'development',
                'software', 'app', 'website', 'internet', 'digital', 'AI', 'ML'
            ],
            'science': [
                'research', 'science', 'scientist', 'discovery', 'experiment',
                'physics', 'chemistry', 'biology', 'mathematics', 'medicine'
            ],
            'business': [
                'business', 'company', 'startup', 'investment', 'economy',
                'market', 'finance', 'money', 'profit', 'sales'
            ],
            'education': [
                'education', 'study', 'university', 'school', 'course',
                'learning', 'student', 'teacher', 'knowledge'
            ],
            'sports': [
                'sport', 'football', 'hockey', 'basketball', 'olympics',
                'training', 'team', 'match', 'competition'
            ],
            'entertainment': [
                'movie', 'film', 'actor', 'music', 'game', 'book',
                'theater', 'concert', 'show', 'television'
            ]
        }
    
    def detect_language(self, text: str) -> str:
        """Detect language of the text"""
        try:
            # Use first 1000 characters for detection
            sample_text = text[:1000] if len(text) > 1000 else text
            language = detect(sample_text)
            logger.debug(f"Detected language: {language}")
            return language
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return 'unknown'
    
    def categorize_article(self, text: str, title: Optional[str] = None) -> List[str]:
        """Categorize article based on content"""
        if not text:
            return ['other']
        
        # Detect language
        language = self.detect_language(text)
        
        # Combine title and text for analysis
        full_text = (title or '') + ' ' + text
        full_text = full_text.lower()
        
        # Choose categories based on language
        if language == 'ru':
            categories_dict = self.categories
        else:
            categories_dict = self.categories_en
        
        # Score each category
        category_scores = {}
        
        for category, keywords in categories_dict.items():
            score = 0
            for keyword in keywords:
                # Count occurrences (simple approach)
                matches = len(re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', full_text))
                score += matches
            
            if score > 0:
                category_scores[category] = score
        
        # Return categories with scores > 0, sorted by score
        if category_scores:
            sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            # Return top 3 categories
            return [cat for cat, score in sorted_categories[:3]]
        
        return ['other']
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract key terms from text using TF-IDF"""
        try:
            # Simple TF-IDF approach
            vectorizer = TfidfVectorizer(
                max_features=max_keywords,
                stop_words='english',  # Basic stop words
                ngram_range=(1, 2),
                min_df=1
            )
            
            # Clean text
            cleaned_text = re.sub(r'[^a-zA-Zа-яА-Я\s]', ' ', text)
            
            tfidf_matrix = vectorizer.fit_transform([cleaned_text])
            feature_names = vectorizer.get_feature_names_out()
            if hasattr(tfidf_matrix, 'toarray'):
                scores = tfidf_matrix.toarray()[0]
            else:
                scores = tfidf_matrix[0].toarray().flatten()
            
            # Get top keywords
            keyword_scores = list(zip(feature_names, scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            return [keyword for keyword, score in keyword_scores if score > 0]
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []