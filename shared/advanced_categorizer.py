"""
Advanced Article Categorizer using UpSkillMe service
Integrates OpenAI-based categorization with embedding similarity
"""
import os
import re
import uuid
import yaml
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from openai import OpenAI
from topic_clusterer import TopicClusterer
from bart_categorizer import BartCategorizer

logger = logging.getLogger(__name__)

class AdvancedCategorizer:
    """Advanced categorizer using LLM + embeddings for precise categorization"""
    
    def __init__(self):
        # Only initialize OpenAI client if API key is available
        if os.getenv("OPENAI_API_KEY"):
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", None)
            )
        else:
            self.client = None
            logger.warning("OpenAI API key not found, advanced categorization will be disabled")
        
        self.embed_model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        self.chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        
        # Load categories configuration
        self.categories = self._load_categories()
        self._primary_embeddings = None
        
        # Initialize topic clusterer
        try:
            self.topic_clusterer = TopicClusterer()
            logger.info("Topic clusterer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize topic clusterer: {e}")
            self.topic_clusterer = None
        
        # Initialize BART categorizer
        try:
            self.bart_categorizer = BartCategorizer()
            logger.info("BART categorizer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize BART categorizer: {e}")
            self.bart_categorizer = None
        
        logger.info("Advanced categorizer initialized")
    
    def _load_categories(self) -> Dict:
        """Load categories from YAML config"""
        categories_path = os.path.join(os.path.dirname(__file__), "categories.yaml")
        try:
            with open(categories_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error("categories.yaml not found, using default categories")
            return {
                "primary": [
                    {"key": "AI", "label": "Искусственный интеллект", "description": "ML, нейросети, LLM"},
                    {"key": "Programming", "label": "Программирование", "description": "Языки, фреймворки, алгоритмы"},
                    {"key": "Business", "label": "Бизнес", "description": "Бизнес-процессы, менеджмент"},
                    {"key": "Other", "label": "Другое", "description": "Прочие темы"}
                ],
                "subcategories": {
                    "AI": ["LLM", "NLP", "Computer Vision"],
                    "Programming": ["Python", "JavaScript", "Testing"],
                    "Business": ["Management", "Strategy"],
                    "Other": ["General"]
                }
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text
    
    def _summarize(self, text: str, title: str = "") -> str:
        """Generate summary using LLM"""
        try:
            content = f"{title}\n\n{text}" if title else text
            content = content[:6000]  # Limit content size
            
            prompt = f"""Суммаризируй текст новости/статьи в 3-5 предложениях на языке исходного текста. 
Выдели основную тему и ключевую мысль.

Текст: ```{content}```"""
            
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "Ты кратко и точно суммируешь тексты."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=220
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return text[:500] + "..." if len(text) > 500 else text
    
    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts"""
        try:
            response = self.client.embeddings.create(
                model=self.embed_model, 
                input=texts
            )
            vectors = [np.array(d.embedding, dtype=np.float32) for d in response.data]
            return np.stack(vectors, axis=0)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return random embeddings as fallback
            return np.random.randn(len(texts), 1536).astype(np.float32)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between vectors"""
        a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
        return np.dot(a_norm, b_norm.T)
    
    def _get_primary_embeddings(self) -> np.ndarray:
        """Get cached primary category embeddings"""
        if self._primary_embeddings is None:
            descriptions = [cat["description"] for cat in self.categories["primary"]]
            self._primary_embeddings = self._embed_texts(descriptions)
        return self._primary_embeddings
    
    def _classify_primary(self, summary: str) -> Tuple[str, float]:
        """Classify primary category using embeddings with improved logic"""
        try:
            query_embedding = self._embed_texts([summary])
            category_embeddings = self._get_primary_embeddings()
            
            similarities = self._cosine_similarity(query_embedding, category_embeddings)[0]
            
            # Get top 3 categories for better analysis
            top_indices = np.argsort(similarities)[-3:][::-1]
            top_similarities = similarities[top_indices]
            
            # Choose best category with improved confidence calculation
            best_idx = top_indices[0]
            raw_confidence = float(top_similarities[0])
            
            # Boost confidence if similarity is strong or multiple categories are close
            if raw_confidence > 0.4 or (len(top_similarities) > 1 and top_similarities[1] > 0.3):
                confidence = min(raw_confidence * 1.2, 0.95)  # Boost but cap at 95%
            else:
                confidence = max(raw_confidence, 0.25)  # Minimum 25%
            
            primary_key = self.categories["primary"][best_idx]["key"]
            return primary_key, confidence
            
        except Exception as e:
            logger.error(f"Error in primary classification: {e}")
            # Enhanced fallback with keyword-based confidence
            fallback_category, confidence = self._fallback_classification(summary)
            return fallback_category, confidence
    
    def _extract_subcategories(self, primary_key: str, summary: str, max_categories: int = 3) -> List[str]:
        """Extract subcategories using keyword matching + LLM fallback"""
        try:
            subcategories = self.categories["subcategories"].get(primary_key, [])
            if not subcategories:
                return []
            
            # First try keyword-based matching for Business category
            if primary_key == "Business":
                summary_lower = summary.lower()
                
                # Tax-related keywords
                if any(word in summary_lower for word in ["налог", "ндфл", "налогообложен", "tax"]):
                    if "Taxes" in subcategories:
                        return ["Taxes"]
                
                # Legal keywords  
                if any(word in summary_lower for word in ["правов", "закон", "юридическ", "legal"]):
                    if "Legal" in subcategories:
                        return ["Legal"]
                
                # Immigration keywords
                if any(word in summary_lower for word in ["эмиграц", "иммиграц", "переезд", "immigration"]):
                    if "Immigration" in subcategories:
                        return ["Immigration"]
                        
                # Investment keywords
                if any(word in summary_lower for word in ["инвестиц", "investment", "инвестор"]):
                    if "Investment" in subcategories:
                        return ["Investment"]
            
            # Career category keyword matching
            if primary_key == "Career":
                summary_lower = summary.lower()
                
                # Job market and positions
                if any(word in summary_lower for word in ["вакансии", "должност", "job", "position", "рынок труда"]):
                    if "Industry Trends" in subcategories:
                        return ["Industry Trends"]
                
                # Interview and skills
                if any(word in summary_lower for word in ["собеседован", "interview", "навыки", "skill"]):
                    if "Interview Prep" in subcategories:
                        return ["Interview Prep"]
            
            # Fallback to LLM for other categories or unclear cases
            prompt = f"""На основе краткого описания статьи выбери до {max_categories} наиболее подходящих подкатегорий из списка.
Дай ответ в виде JSON массива только с выбранными строками, без комментариев.

Доступные подкатегории: {subcategories}

Описание статьи: {summary}"""
            
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "Ты классифицируешь статьи по подкатегориям. Отвечай только в формате JSON массива."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            result_text = response.choices[0].message.content.strip()
            # Try to parse as JSON
            import json
            try:
                result = json.loads(result_text)
                if isinstance(result, list):
                    return [sub for sub in result if sub in subcategories][:max_categories]
            except json.JSONDecodeError:
                pass
            
            # Fallback: return first subcategory
            return [subcategories[0]] if subcategories else []
            
        except Exception as e:
            logger.error(f"Error extracting subcategories: {e}")
            return []
    
    def _extract_keywords(self, summary: str, max_keywords: int = 8) -> List[str]:
        """Extract keywords using LLM"""
        try:
            prompt = f"""Извлеки до {max_keywords} ключевых слов из текста статьи.
Дай ответ в виде JSON массива строк без комментариев.

Текст: {summary}"""
            
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "Ты извлекаешь ключевые слова из текстов. Отвечай только в формате JSON массива."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            # Try to parse as JSON
            import json
            try:
                result = json.loads(result_text)
                if isinstance(result, list):
                    return [str(kw) for kw in result[:max_keywords]]
            except json.JSONDecodeError:
                pass
            
            # Fallback: simple keyword extraction
            words = summary.split()
            return [w for w in words if len(w) > 4][:max_keywords]
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    async def categorize_article(self, text: str, title: str = "", language: str = "auto", extracted_keywords: list = None) -> Dict:
        """
        Main categorization method
        
        Args:
            text: Article text
            title: Article title (optional)
            language: Language hint (auto/ru/en)
            
        Returns:
            Dict with categorization results
        """
        try:
            # Clean input text
            clean_text = self._clean_text(text)
            clean_title = self._clean_text(title)
            
            if not clean_text and not clean_title:
                raise ValueError("No text content provided")
            
            # Generate summary
            logger.info("=== НАЧАЛО ДЕТАЛЬНОГО АНАЛИЗА СТАТЬИ ===")
            logger.info(f"📝 Текст для анализа: {len(clean_text)} символов")
            logger.info(f"📰 Заголовок: '{clean_title}'")
            
            logger.info("🔄 ЭТАП 1: Генерация краткого содержания...")
            summary = self._summarize(clean_text, clean_title)
            logger.info(f"✅ Краткое содержание создано ({len(summary)} символов)")
            logger.info(f"📋 Содержание: {summary[:200]}...")
            
            # Primary category classification
            logger.info("🔄 ЭТАП 2: AI классификация основной категории...")
            primary_key, confidence = self._classify_primary(summary)
            logger.info(f"✅ AI классификация: {primary_key} (уверенность: {confidence:.2%})")
            
            # Get primary category label
            primary_label = next(
                (cat["label"] for cat in self.categories["primary"] if cat["key"] == primary_key),
                primary_key
            )
            
            # Extract subcategories
            logger.info("🔄 ЭТАП 3a: Извлечение подкатегорий...")
            subcategories = self._extract_subcategories(primary_key, summary)
            logger.info(f"✅ Подкатегории: {subcategories}")
            
            # Use extracted keywords from HTML if available, otherwise extract from text
            logger.info("🔄 ЭТАП 3b: Извлечение ключевых слов...")
            if extracted_keywords:
                logger.info(f"✅ Используем ключевые слова из HTML: {extracted_keywords}")
                keywords = extracted_keywords[:8]  # Limit to 8 keywords
            else:
                logger.info("🔄 Извлекаем ключевые слова из текста...")
                keywords = self._extract_keywords(summary)
                logger.info(f"✅ Извлеченные ключевые слова: {keywords}")
            
            # Topic clustering (semantic analysis)
            logger.info("🔄 ЭТАП 4: Тематическая кластеризация (TF-IDF)...")
            topic_result = None
            if self.topic_clusterer:
                try:
                    topic_result = self.topic_clusterer.cluster_document(clean_text, clean_title)
                    if topic_result:
                        logger.info(f"✅ Тематическая кластеризация:")
                        logger.info(f"   📊 Тема: {topic_result.get('topic_label', 'Неизвестно')}")
                        logger.info(f"   🏷️ Ключевые термины: {topic_result.get('topic_keywords', [])}")
                        logger.info(f"   📈 Уверенность: {topic_result.get('confidence', 0):.1%}")
                    else:
                        logger.warning("⚠️ Тематическая кластеризация не дала результата")
                except Exception as e:
                    logger.error(f"❌ Ошибка тематической кластеризации: {e}")
            else:
                logger.warning("⚠️ Тематическая кластеризация недоступна")
            
            # BART categorization (zero-shot classification)
            logger.info("🔄 ЭТАП 5: BART/Rule-based классификация...")
            bart_result = None
            if self.bart_categorizer:
                try:
                    bart_result = self.bart_categorizer.categorize_article(clean_text, clean_title)
                    if bart_result:
                        method = bart_result.get('method', 'unknown')
                        logger.info(f"✅ Дополнительная классификация ({method}):")
                        logger.info(f"   🎯 Категория: {bart_result.get('primary_category', 'Неизвестно')}")
                        logger.info(f"   🎲 Уверенность: {bart_result.get('confidence', 0):.1%}")
                        if bart_result.get('matched_keywords'):
                            logger.info(f"   🔑 Найденные термины: {bart_result['matched_keywords']}")
                    else:
                        logger.warning("⚠️ Дополнительная классификация не дала результата")
                except Exception as e:
                    logger.error(f"❌ Ошибка дополнительной классификации: {e}")
            else:
                logger.warning("⚠️ Дополнительная классификация недоступна")
            
            result = {
                "id": str(uuid.uuid4()),
                "title": clean_title or None,
                "summary": summary,
                # AI-based structured categorization
                "ai_categorization": {
                    "primary_category": primary_key,
                    "primary_category_label": primary_label,
                    "subcategories": subcategories,
                    "keywords": keywords,
                    "confidence": confidence,
                    "method": "openai_embeddings"
                },
                # Topic clustering categorization
                "topic_clustering": topic_result,
                # BART zero-shot categorization
                "bart_categorization": bart_result,
                # Legacy fields for backward compatibility
                "primary_category": primary_key,
                "primary_category_label": primary_label,
                "subcategories": subcategories,
                "keywords": keywords,
                "confidence": confidence
            }
            
            logger.info("=== ЗАВЕРШЕНИЕ АНАЛИЗА ===")
            logger.info(f"🎉 Итоговая категоризация: {primary_key} (уверенность: {confidence:.2f})")
            logger.info("📊 Все алгоритмы выполнены успешно")
            logger.info("=" * 50)
            return result
            
        except Exception as e:
            logger.error(f"Categorization failed: {e}")
            raise
    
    def _fallback_classification(self, text: str) -> Tuple[str, float]:
        """Enhanced fallback classification based on keywords"""
        text_lower = text.lower()
        
        # Category keyword mapping with weights
        category_keywords = {
            "AI": {
                "keywords": ["ai", "машинное обучение", "нейросети", "llm", "nlp", "генеративные модели", 
                           "искусственный интеллект", "computer vision", "mlops"],
                "weight": 0.9
            },
            "Programming": {
                "keywords": ["программирование", "разработка", "код", "алгоритм", "python", "javascript", 
                           "технологии", "software", "development", "coding", "фреймворки"],
                "weight": 0.8
            },
            "Business": {
                "keywords": ["бизнес", "деньги", "финансы", "стартап", "менеджмент", "маркетинг", 
                           "business", "finance", "startup", "investment", "продажи", "налоги", "налогообложение", 
                           "фнс", "налоговое", "резидентство", "эмиграция", "налоговое право", "ндфл"],
                "weight": 0.8
            },
            "Data": {
                "keywords": ["данные", "аналитика", "data", "analytics", "bi", "sql", "статистика", 
                           "data engineering", "визуализация"],
                "weight": 0.7
            },
            "Architecture": {
                "keywords": ["архитектура", "системы", "микросервисы", "ddd", "интеграции", 
                           "распределённые системы", "системный анализ"],
                "weight": 0.7
            },
            "Security": {
                "keywords": ["безопасность", "security", "криптография", "iam", "апpsec", 
                           "нормативы", "compliance"],
                "weight": 0.7
            }
        }
        
        best_category = "Other"
        best_score = 0.0
        
        for category, data in category_keywords.items():
            score = 0
            for keyword in data["keywords"]:
                if keyword in text_lower:
                    score += 1
            
            # Normalize score and apply weight
            if score > 0:
                normalized_score = min(score / len(data["keywords"]) * data["weight"], 0.9)
                if normalized_score > best_score:
                    best_score = normalized_score
                    best_category = category
        
        # Ensure minimum confidence of 0.25 if keywords found, 0.15 otherwise
        confidence = max(best_score, 0.25 if best_score > 0 else 0.15)
        
        return best_category, confidence

    def is_available(self) -> bool:
        """Check if OpenAI API key is available"""
        return bool(self.client and os.getenv("OPENAI_API_KEY"))