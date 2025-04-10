from utils.BaseProcessor import BaseProcessor
from bs4 import BeautifulSoup
import html
import re
import unicodedata
from utils.market_session import MarketSessionClassifier


class NewsProcessor(BaseProcessor):
    """News-specific processor implementation"""
    
    def __init__(self, event_trader_redis, delete_raw: bool = True, polygon_subscription_delay: int = None, ttl=None):
        super().__init__(event_trader_redis, delete_raw, polygon_subscription_delay)
        # Any news-specific initialization can go here
        # self.market_session = MarketSessionClassifier() 
        self.ttl = ttl
        
    def process_all_news(self):
        """Maintain original method name for backward compatibility"""
        return self.process_all_items()

    def _standardize_fields(self, content: dict) -> dict:
        """News already has standard fields"""
        return content  # Already standardized
    

    def _clean_content(self, content: dict) -> dict:
        """Implement abstract method with news-specific cleaning"""
        return self._clean_news(content)


    def _clean_news(self, news: dict) -> dict:
        """Clean news content.
        
        Process order:
        1. Clean text content (title, teaser, body)
        2. Convert timestamps to Eastern
        3. Limit body word count
        
        Args:
            news (dict): Raw news dictionary
        Returns:
            dict: Processed news dictionary
        """
        try:
            cleaned = news.copy()

            # 1. Clean text content
            for field in ['title', 'teaser', 'body']:
                if field in cleaned:
                    cleaned[field] = self._clean_text_content(cleaned[field])

            # 2. Convert timestamps
            for field in ['created', 'updated']:
                if field in cleaned:
                    cleaned[field] = self.convert_to_eastern(cleaned[field])

            # 3. Apply word limit on body
            cleaned = self._limit_body_word_count(cleaned)

            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error in _clean_news: {e}")
            return news  # Return original if cleaning fails


    def _clean_text_content(self, content: str) -> str:
        """Clean individual text content"""
        if content is None or not isinstance(content, str):
            return content

        if content.startswith(('http://', 'https://', '/')):
            return content
                
        try:
            cleaned_text = BeautifulSoup(content, 'html.parser').get_text(' ')
            
            # Convert HTML entities like &quot; to "
            cleaned_text = html.unescape(cleaned_text)

            # Detect if content is code (basic heuristic)
            is_code = re.search(r"def |print\(|\{.*?\}|=", cleaned_text)

            # Normalize Unicode (fix \u201c, \u201d, etc.) ONLY if it's not code
            if not is_code:
                cleaned_text = unicodedata.normalize("NFKC", cleaned_text)

            cleaned_text = cleaned_text.replace('\xa0', ' ')
            cleaned_text = re.sub(r'\s+([.,;?!])', r'\1', cleaned_text)
            cleaned_text = re.sub(r'([.,;?!])\s+', r'\1 ', cleaned_text)
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            return cleaned_text.strip()
        except Exception as e:
            self.logger.error(f"Error cleaning content: {e}")
            return content  # Return original if cleaning fails
        


    def _limit_body_word_count(self, news: dict, max_words: int = 3000) -> dict:
        """Limit word count of the 'body' key in the news dictionary.
        
        Args:
            news (dict): The news dictionary
            max_words (int): Maximum allowed words in the 'body' field (default: 800)
        
        Returns:
            dict: News dictionary with truncated 'body' if necessary
        """
        try:
            if 'body' not in news or not isinstance(news['body'], str):
                self.logger.info(f"Body not found in news: {news}")
                return news
            
            words = [w for w in news['body'].split() if w.strip()]
            
            if len(words) <= max_words:  # Skip processing if already within limit
                self.logger.debug(f"Body already within limit: {len(words)} words")
                return news
            
            news['body'] = ' '.join(words[:max_words]).strip() + "..."
            self.logger.debug(f"Truncated body from {len(words)} to {max_words} words")
            
            return news
        
        except Exception as e:
            self.logger.error(f"Error limiting body word count: {e}")
            return news  # Return original if processing fails

