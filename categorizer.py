"""
Article categorization and filtering logic
"""
import json
import logging
from openai import OpenAI
import os
import re

logger = logging.getLogger(__name__)

class ArticleCategorizer:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Define relevant categories
        self.categories = {
            'ai_ml': ['artificial intelligence', 'machine learning', 'deep learning', 'neural networks', 'llm', 'gpt', 'ai'],
            'system_design': ['system design', 'architecture', 'scalability', 'microservices', 'distributed systems'],
            'programming': ['programming', 'coding', 'software development', 'python', 'javascript', 'backend', 'frontend'],
            'devops': ['devops', 'docker', 'kubernetes', 'deployment', 'ci/cd', 'infrastructure'],
            'data': ['data science', 'analytics', 'big data', 'database', 'sql', 'nosql'],
            'tech_trends': ['technology trends', 'startup', 'innovation', 'tech news'],
            'irrelevant': []
        }
    
    def filter_by_tags(self, article, allowed_tags):
        """First stage filtering based on RSS tags"""
        try:
            article_tags = article.get('tags', [])
            
            if not article_tags:
                logger.debug(f"No tags found for article: {article.get('title', 'Unknown')}")
                # If no tags, proceed to content-based filtering
                return True
            
            # Convert allowed tags to lowercase for comparison
            allowed_tags_lower = [tag.lower().strip() for tag in allowed_tags]
            
            # Check if any article tag matches allowed tags
            for tag in article_tags:
                tag_lower = tag.lower().strip()
                for allowed_tag in allowed_tags_lower:
                    if allowed_tag in tag_lower or tag_lower in allowed_tag:
                        logger.debug(f"Article passed tag filter: {tag} matches {allowed_tag}")
                        return True
            
            logger.debug(f"Article filtered out by tags: {article_tags}")
            return False
            
        except Exception as e:
            logger.error(f"Error in tag filtering: {str(e)}")
            # In case of error, proceed to content-based filtering
            return True
    
    def categorize_by_content(self, text):
        """Second stage categorization based on article content"""
        try:
            if not text or len(text) < 100:
                logger.debug("Text too short for categorization")
                return 'irrelevant'
            
            # Truncate text if too long (GPT token limits)
            if len(text) > 4000:
                text = text[:4000] + "..."
            
            prompt = f"""
            Analyze the following article text and categorize it into one of these categories:
            - ai_ml: Articles about artificial intelligence, machine learning, neural networks, LLMs
            - system_design: Articles about system architecture, scalability, distributed systems
            - programming: Articles about programming languages, software development, coding practices
            - devops: Articles about DevOps, deployment, infrastructure, containers
            - data: Articles about data science, analytics, databases
            - tech_trends: Articles about technology trends, startups, innovation
            - irrelevant: Articles that don't fit the above categories or are not technical
            
            Respond with JSON in this format: {{"category": "category_name", "confidence": 0.8, "reasoning": "brief explanation"}}
            
            Article text:
            {text}
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at categorizing technical articles. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=200,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            category = result.get('category', 'irrelevant')
            confidence = result.get('confidence', 0.0)
            reasoning = result.get('reasoning', '')
            
            logger.info(f"Categorized as '{category}' with confidence {confidence}: {reasoning}")
            
            # Filter out low confidence categorizations
            if confidence < 0.6:
                logger.debug(f"Low confidence categorization ({confidence}), marking as irrelevant")
                return 'irrelevant'
            
            return category
            
        except Exception as e:
            logger.error(f"Error in content categorization: {str(e)}")
            return 'irrelevant'
    
    def is_duplicate(self, text, existing_articles, threshold=0.8):
        """Check if article is similar to existing articles"""
        try:
            if not existing_articles:
                return False
            
            # Simple similarity check based on title and key phrases
            # In production, you might want to use embeddings for better similarity detection
            text_lower = text.lower()
            words = set(re.findall(r'\w+', text_lower))
            
            for existing in existing_articles:
                existing_lower = existing.lower()
                existing_words = set(re.findall(r'\w+', existing_lower))
                
                # Calculate Jaccard similarity
                intersection = len(words.intersection(existing_words))
                union = len(words.union(existing_words))
                
                if union > 0:
                    similarity = intersection / union
                    if similarity > threshold:
                        logger.info(f"Duplicate detected with similarity {similarity}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in duplicate detection: {str(e)}")
            return False
    
    def extract_keywords(self, text):
        """Extract key technical terms from article"""
        try:
            prompt = f"""
            Extract the most important technical keywords and concepts from this article.
            Return a list of 5-10 key terms that best represent the article's content.
            Focus on technical terms, technologies, methodologies, and concepts.
            
            Respond with JSON in this format: {{"keywords": ["keyword1", "keyword2", ...]}}
            
            Article text:
            {text[:2000]}
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting technical keywords. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            keywords = result.get('keywords', [])
            
            logger.debug(f"Extracted keywords: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []
