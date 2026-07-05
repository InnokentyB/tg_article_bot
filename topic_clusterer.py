"""
Topic clustering using sentence transformers and clustering algorithms
Alternative to BERTopic for semantic topic discovery
"""
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
try:
    from sklearn.cluster import KMeans, AgglomerativeClustering
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
# from sentence_transformers import SentenceTransformer  # Not available in this environment
import re

# Russian stop words
RUSSIAN_STOP_WORDS = {
    'а', 'без', 'более', 'быть', 'в', 'вам', 'вас', 'весь', 'во', 'вот', 'все', 'всего', 'всех',
    'вы', 'где', 'да', 'даже', 'для', 'до', 'его', 'ее', 'если', 'есть', 'еще', 'же', 'за', 'здесь',
    'и', 'из', 'или', 'им', 'их', 'к', 'как', 'ко', 'когда', 'кто', 'ли', 'либо', 'мне', 'может',
    'мы', 'на', 'над', 'надо', 'наш', 'не', 'него', 'нее', 'нет', 'ни', 'них', 'но', 'ну', 'о',
    'об', 'один', 'он', 'она', 'они', 'оно', 'от', 'по', 'под', 'при', 'с', 'со', 'та', 'так',
    'такой', 'там', 'те', 'тем', 'то', 'того', 'тоже', 'той', 'только', 'том', 'ты', 'у', 'уже',
    'хотя', 'чего', 'чем', 'что', 'чтобы', 'чье', 'эта', 'эти', 'это', 'я', 'будет', 'если',
    'была', 'были', 'был', 'быть', 'можно', 'нужно', 'очень', 'через', 'между', 'после',
    'лучше', 'самый', 'другой', 'новый', 'большой', 'первый', 'последний', 'хороший', 'плохой'
}

logger = logging.getLogger(__name__)

class TopicClusterer:
    """
    Topic clustering using BERT embeddings and clustering algorithms
    Provides semantic topic discovery similar to BERTopic
    """
    
    def __init__(self):
        """
        Initialize topic clusterer using TF-IDF vectors and sklearn clustering
        """
        self.topic_labels = []
        self.topic_keywords = {}
        logger.info("Topic clusterer initialized with TF-IDF + K-means")
    
    def _clean_text(self, text: str) -> str:
        """Clean text for processing"""
        if not text:
            return ""
        
        # Remove URLs and special characters
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        text = re.sub(r'[^\w\s\u0400-\u04FF]', ' ', text)  # Keep Cyrillic
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_topic_keywords(self, documents: List[str], cluster_labels: np.ndarray) -> Dict[int, List[str]]:
        """Extract representative keywords for each topic cluster"""
        topic_keywords = {}
        
        try:
            # Use TF-IDF to find characteristic words for each cluster
            # Focus on meaningful phrases and terms
            vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words=list(RUSSIAN_STOP_WORDS),  # Use Russian stop words
                ngram_range=(1, 3),  # Include 1-3 word phrases 
                min_df=1,  # Allow rare terms for single document
                token_pattern=r'[a-zA-Zа-яё]+',  # Only letters, no punctuation
                lowercase=True
            )
            
            tfidf_matrix = vectorizer.fit_transform(documents)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get unique cluster labels
            unique_labels = np.unique(cluster_labels)
            
            for label in unique_labels:
                if label == -1:  # Skip noise cluster
                    continue
                    
                # Get documents in this cluster
                cluster_mask = cluster_labels == label
                cluster_tfidf = tfidf_matrix[cluster_mask]
                
                # Calculate mean TF-IDF scores for this cluster
                mean_scores = np.array(cluster_tfidf.mean(axis=0)).flatten()
                
                # Get top keywords with better filtering
                scored_features = [(feature_names[i], mean_scores[i]) for i in range(len(feature_names)) 
                                 if mean_scores[i] > 0.001]
                
                # Sort by score, boost longer phrases
                scored_features.sort(key=lambda x: x[1] + (len(x[0].split()) * 0.15), reverse=True)
                
                # Filter meaningful keywords with better logic
                cluster_keywords = []
                seen_roots = set()  # Avoid similar word forms
                
                for keyword, score in scored_features[:25]:
                    if (len(keyword) >= 3 and 
                        not keyword.isdigit() and
                        keyword not in RUSSIAN_STOP_WORDS and
                        not any(char.isdigit() for char in keyword)):
                        
                        # Check if this is a better version of already seen word
                        word_root = keyword[:4] if len(keyword) > 4 else keyword[:3]
                        
                        # Prefer longer, more specific terms and nominative forms
                        is_better_term = (
                            len(keyword) > 6 or  # Long compound words
                            ' ' in keyword or    # Multi-word phrases
                            keyword.endswith(('ание', 'ение', 'ость', 'ство', 'тель', 'ция')) or  # Noun endings
                            keyword.endswith(('ный', 'ская', 'ское'))  # Adjective endings
                        )
                        
                        if word_root not in seen_roots or is_better_term:
                            cluster_keywords.append(keyword)
                            seen_roots.add(word_root)
                        
                        if len(cluster_keywords) >= 6:
                            break
                
                topic_keywords[label] = cluster_keywords
                
        except Exception as e:
            logger.error(f"Error extracting topic keywords: {e}")
            
        return topic_keywords
    
    def _generate_topic_labels(self, topic_keywords: Dict[int, List[str]]) -> Dict[int, str]:
        """Generate human-readable labels for topics based on keywords"""
        topic_labels = {}
        
        for topic_id, keywords in topic_keywords.items():
            if not keywords:
                topic_labels[topic_id] = f"Тема {topic_id}"
                continue
            
            # Filter and clean keywords - focus on meaningful terms
            meaningful_keywords = []
            for kw in keywords[:8]:  # Consider top 8
                # Prioritize compound words and meaningful terms
                if (len(kw) > 2 and 
                    not kw.isdigit() and
                    kw not in RUSSIAN_STOP_WORDS and
                    not any(char.isdigit() for char in kw)):
                    # Prefer compound words and nouns in nominative case
                    if ('ани' in kw or 'ени' in kw or 'ост' in kw or 
                        'ств' in kw or 'тор' in kw or 'ние' in kw or
                        len(kw) > 6 or ' ' in kw):  # Compound words or longer terms
                        meaningful_keywords.insert(0, kw)  # Put at front
                    else:
                        meaningful_keywords.append(kw)
            
            # If still no keywords, use original list
            if not meaningful_keywords and keywords:
                meaningful_keywords = keywords[:3]  # Take top 3 original keywords
            
            if not meaningful_keywords:
                topic_labels[topic_id] = f"Тема {topic_id}"
                continue
            
            # Create label from meaningful keywords
            if len(meaningful_keywords) == 1:
                label = meaningful_keywords[0].title()
            elif len(meaningful_keywords) == 2:
                label = f"{meaningful_keywords[0]} • {meaningful_keywords[1]}"
            else:
                # For 3+ keywords, create thematic grouping
                main_kw = meaningful_keywords[0]
                related = meaningful_keywords[1]
                label = f"{main_kw} ({related})"
            
            # Limit label length
            if len(label) > 40:
                label = label[:37] + "..."
                
            topic_labels[topic_id] = label
            
        return topic_labels
    
    def cluster_document(self, text: str, title: str = "") -> Dict:
        """
        Cluster a single document and find its topic using TF-IDF analysis
        
        Args:
            text: Document text
            title: Document title (optional)
            
        Returns:
            Dict with clustering results
        """
        try:
            logger.info("   🔍 Начинаем тематическую кластеризацию...")
            
            # Prepare text
            full_text = f"{title} {text}" if title else text
            clean_text = self._clean_text(full_text)
            logger.info(f"   📝 Подготовлен текст: {len(clean_text)} символов")
            
            if len(clean_text) < 20:
                logger.warning("   ⚠️ Текст слишком короткий для кластеризации")
                return {
                    "topic_id": -1,
                    "topic_label": "Текст слишком короткий",
                    "topic_keywords": [],
                    "confidence": 0.0,
                    "method": "tfidf_clustering"
                }
            
            # Extract keywords using TF-IDF - optimized for single document
            logger.info("   🔧 Запуск TF-IDF анализа...")
            try:
                # For single document, use different approach
                vectorizer = TfidfVectorizer(
                    max_features=100,
                    ngram_range=(1, 2),  # Reduce ngram range
                    stop_words=list(RUSSIAN_STOP_WORDS),
                    min_df=1,
                    lowercase=True,
                    token_pattern=r'\b[а-яё]{3,}\b'  # Only Russian words 3+ chars
                )
                
                # Add some dummy documents to make TF-IDF work better
                dummy_docs = [
                    clean_text,
                    "программирование разработка код",
                    "управление проект команда", 
                    "анализ данные исследование"
                ]
                
                tfidf_matrix = vectorizer.fit_transform(dummy_docs)
                feature_names = vectorizer.get_feature_names_out()
                
                # Get scores for our main document (first one)
                scores = tfidf_matrix.toarray()[0]
                
                # Get top keywords with more lenient threshold
                top_indices = np.argsort(scores)[-8:][::-1]
                keywords = [
                    feature_names[i] for i in top_indices 
                    if scores[i] > 0.001 and len(feature_names[i]) > 2
                ]
                
                # Clean keywords - remove very short or common words
                cleaned_keywords = []
                for kw in keywords:
                    if len(kw) > 2 and not kw.isdigit():
                        cleaned_keywords.append(kw)
                
                keywords = cleaned_keywords[:6]
                
            except Exception:
                keywords = []
            
            # Generate topic label from keywords
            if keywords:
                topic_label = " • ".join(keywords[:3])
                if len(topic_label) > 50:
                    topic_label = topic_label[:47] + "..."
            else:
                topic_label = "Общая тема"
                
            # Calculate confidence based on keyword diversity and scores
            confidence = 0.6
            if len(keywords) >= 3:
                confidence = 0.75
            if len(keywords) >= 5:
                confidence = 0.85
                
            return {
                "topic_id": 0,
                "topic_label": topic_label,
                "topic_keywords": keywords,
                "confidence": confidence,
                "method": "tfidf_clustering"
            }
            
        except Exception as e:
            logger.error(f"Error in topic clustering: {e}")
            return {
                "topic_id": -1,
                "topic_label": "Ошибка кластеризации",
                "topic_keywords": [],
                "confidence": 0.0,
                "method": "tfidf_clustering"
            }
    
    def cluster_documents(self, documents: List[str], titles: List[str] = None, n_clusters: int = 5) -> List[Dict]:
        """
        Cluster multiple documents using TF-IDF vectors and K-means
        
        Args:
            documents: List of document texts
            titles: List of document titles (optional)
            n_clusters: Number of clusters to create
            
        Returns:
            List of clustering results for each document
        """
        if len(documents) < 2:
            return [self.cluster_document(doc, titles[i] if titles else "") 
                   for i, doc in enumerate(documents)]
        
        try:
            # Prepare texts
            if titles:
                full_texts = [f"{titles[i]} {doc}" if i < len(titles) else doc 
                             for i, doc in enumerate(documents)]
            else:
                full_texts = documents
                
            clean_texts = [self._clean_text(text) for text in full_texts]
            
            # Filter out very short texts
            valid_indices = [i for i, text in enumerate(clean_texts) if len(text) >= 20]
            if len(valid_indices) < 2:
                return [self.cluster_document(doc, titles[i] if titles else "") 
                       for i, doc in enumerate(documents)]
            
            valid_texts = [clean_texts[i] for i in valid_indices]
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 3),
                stop_words=None,
                min_df=1,
                max_df=0.95
            )
            
            tfidf_matrix = vectorizer.fit_transform(valid_texts)
            
            # Perform K-means clustering
            n_clusters = min(n_clusters, len(valid_texts) // 2, 8)  # Reasonable cluster count
            if n_clusters < 2:
                n_clusters = 2
                
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = clusterer.fit_predict(tfidf_matrix.toarray())
            
            # Extract topic keywords for each cluster
            topic_keywords = self._extract_topic_keywords(valid_texts, cluster_labels)
            topic_labels = self._generate_topic_labels(topic_keywords)
            
            # Calculate confidence scores based on TF-IDF similarity to cluster center
            confidences = []
            for i, label in enumerate(cluster_labels):
                # Calculate similarity to other documents in the same cluster
                cluster_mask = cluster_labels == label
                if np.sum(cluster_mask) > 1:
                    cluster_docs = tfidf_matrix[cluster_mask]
                    similarities = cosine_similarity(tfidf_matrix[i:i+1], cluster_docs).flatten()
                    confidence = np.mean(similarities)
                else:
                    confidence = 0.5  # Default for single-document clusters
                    
                confidences.append(max(0.1, min(0.95, confidence)))
            
            # Prepare results
            results = []
            valid_idx = 0
            
            for i in range(len(documents)):
                if i in valid_indices:
                    label = cluster_labels[valid_idx]
                    result = {
                        "topic_id": int(label),
                        "topic_label": topic_labels.get(label, f"Кластер {label}"),
                        "topic_keywords": topic_keywords.get(label, []),
                        "confidence": confidences[valid_idx],
                        "method": "tfidf_clustering"
                    }
                    valid_idx += 1
                else:
                    # Fallback for short documents
                    result = self.cluster_document(documents[i], titles[i] if titles else "")
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch topic clustering: {e}")
            return [self.cluster_document(doc, titles[i] if titles else "") 
                   for i, doc in enumerate(documents)]
    
    def is_available(self) -> bool:
        """Check if topic clustering is available"""
        return SKLEARN_AVAILABLE