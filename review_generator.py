"""
AI-powered review generation for articles
"""
import logging
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

class ReviewGenerator:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def generate_review(self, text, title=""):
        """Generate a concise editorial review of the article"""
        try:
            if not text:
                logger.error("No text provided for review generation")
                return ""
            
            # Truncate text if too long
            if len(text) > 3000:
                text = text[:3000] + "..."
            
            title_context = f"Title: {title}\n\n" if title else ""
            
            prompt = f"""
            Ты ведёшь канал с короткими, умными ревью на профессиональные статьи. Напиши обзор в стиле:
            — живой, без пафоса
            — редакторский, чуть ироничный
            — 300–500 символов, без клише
            — сосредоточься на ключевых идеях и практической ценности
            — добавь одну конкретную мысль о том, кому это будет полезно
            
            {title_context}Текст статьи:
            {text}
            
            Напиши только текст ревью, без заголовков и лишних слов.
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты опытный технический редактор, который пишет краткие, остроумные обзоры статей для профессиональной аудитории."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            review = response.choices[0].message.content.strip()
            
            # Validate review length
            if len(review) < 200:
                logger.warning(f"Generated review too short ({len(review)} chars), trying again")
                return self._generate_longer_review(text, title)
            
            if len(review) > 600:
                logger.warning(f"Generated review too long ({len(review)} chars), truncating")
                review = review[:500] + "..."
            
            logger.info(f"Generated review ({len(review)} chars): {review[:100]}...")
            return review
            
        except Exception as e:
            logger.error(f"Error generating review: {str(e)}")
            return self._generate_fallback_review(title, text)
    
    def _generate_longer_review(self, text, title=""):
        """Generate a longer review if the first attempt was too short"""
        try:
            title_context = f"Title: {title}\n\n" if title else ""
            
            prompt = f"""
            Напиши развёрнутый обзор этой статьи (400-500 символов):
            - Объясни главную идею простыми словами
            - Укажи практическую пользу
            - Добавь своё мнение о качестве материала
            - Напиши, кому стоит прочитать
            
            {title_context}Текст статьи:
            {text[:2000]}
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты пишешь подробные, но сжатые обзоры технических статей."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.6
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating longer review: {str(e)}")
            return self._generate_fallback_review(title, text)
    
    def _generate_fallback_review(self, title, text):
        """Generate a simple fallback review"""
        try:
            # Extract first meaningful sentence or paragraph
            sentences = text.split('.')[:3]
            summary = '. '.join(sentences).strip()
            
            if len(summary) > 300:
                summary = summary[:300] + "..."
            
            fallback = f"Интересная статья о {title.lower() if title else 'техническом вопросе'}. {summary}"
            
            if len(fallback) < 300:
                fallback += " Стоит прочитать тем, кто работает с современными технологиями."
            
            return fallback[:500]
            
        except Exception as e:
            logger.error(f"Error generating fallback review: {str(e)}")
            return "Техническая статья с полезной информацией для разработчиков."
    
    def generate_summary(self, text, max_length=200):
        """Generate a brief summary of the article"""
        try:
            if not text:
                return ""
            
            if len(text) > 2000:
                text = text[:2000] + "..."
            
            prompt = f"""
            Создай краткое резюме этой статьи в 1-2 предложениях (максимум {max_length} символов).
            Сосредоточься на главной мысли и ключевых выводах.
            
            Текст статьи:
            {text}
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты создаёшь краткие, информативные резюме технических статей."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return ""
