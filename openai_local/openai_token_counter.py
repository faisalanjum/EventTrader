"""
Token counting and text truncation utilities for OpenAI API requests
Based on tiktoken for precise token counts with the same tokenizer used by OpenAI.
"""

import tiktoken
import logging
from typing import List, Optional, Union, Dict

logger = logging.getLogger(__name__)

class OpenAITokenCounter:
    """
    Utility class for OpenAI token counting and text truncation using tiktoken.
    Uses the exact tokenizers that OpenAI uses for their models.
    """
    # Cache tokenizers for performance - avoid creating new ones for each call
    _tokenizers = {}
    
    # Map of model names to encoding names
    _encoding_map = {
        # GPT models
        "gpt-4": "cl100k_base",
        "gpt-4o": "cl100k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        # Text embedding models
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
        "text-embedding-ada-002": "cl100k_base",
    }
    
    # Token limits for different models
    _token_limits = {
        # Embedding models
        "text-embedding-3-small": 8191,
        "text-embedding-3-large": 8191,
        "text-embedding-ada-002": 8191,
        # Chat models
        "gpt-4": 8192,
        "gpt-4o": 128000,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 16385,
    }
    
    @classmethod
    def get_tokenizer(cls, model: str):
        """Get the appropriate tokenizer for a given model"""
        if model in cls._tokenizers:
            return cls._tokenizers[model]
        
        # Get the encoding name for this model
        encoding_name = cls._encoding_map.get(model)
        if not encoding_name:
            # Default to cl100k_base for newer models
            logger.warning(f"No specific encoding found for {model}, using cl100k_base")
            encoding_name = "cl100k_base"
        
        # Create and cache the tokenizer
        try:
            tokenizer = tiktoken.get_encoding(encoding_name)
            cls._tokenizers[model] = tokenizer
            return tokenizer
        except Exception as e:
            logger.error(f"Error getting tokenizer for model {model}: {e}")
            # Fallback to cl100k_base which is used by most current models
            try:
                tokenizer = tiktoken.get_encoding("cl100k_base")
                cls._tokenizers[model] = tokenizer
                return tokenizer
            except Exception as e2:
                logger.error(f"Error getting fallback tokenizer: {e2}")
                raise
    
    @classmethod
    def count_tokens(cls, text: str, model: str = "text-embedding-3-large") -> int:
        """
        Count tokens in text using the correct tokenizer for the specified model.
        
        Args:
            text: The text to count tokens for
            model: The model to use for token counting
            
        Returns:
            int: The number of tokens in the text
        """
        if not text:
            return 0
            
        tokenizer = cls.get_tokenizer(model)
        tokens = tokenizer.encode(text)
        return len(tokens)
    
    @classmethod
    def count_tokens_batch(cls, texts: List[str], model: str = "text-embedding-3-large") -> List[int]:
        """
        Count tokens for multiple texts using the correct tokenizer.
        
        Args:
            texts: List of texts to count tokens for
            model: The model to use for token counting
            
        Returns:
            List[int]: The number of tokens in each text
        """
        tokenizer = cls.get_tokenizer(model)
        return [len(tokenizer.encode(text)) for text in texts]
    
    @classmethod
    def truncate_text_to_token_limit(cls, 
                                    text: str, 
                                    model: str = "text-embedding-3-large", 
                                    max_tokens: Optional[int] = None) -> str:
        """
        Truncate text to fit within the token limit for the specified model.
        
        Args:
            text: The text to truncate
            model: The model to use for token counting
            max_tokens: Optional custom token limit, defaults to model's limit
            
        Returns:
            str: The truncated text
        """
        if not text:
            return ""
            
        tokenizer = cls.get_tokenizer(model)
        
        # Get the token limit for this model
        if max_tokens is None:
            max_tokens = cls._token_limits.get(model, 8191)  # Default to 8191 if not specified
        
        # Get all tokens for the text
        tokens = tokenizer.encode(text)
        
        # Check if truncation is needed
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate to max_tokens
        truncated_tokens = tokens[:max_tokens]
        truncated_text = tokenizer.decode(truncated_tokens)
        
        logger.info(f"Truncated text from {len(tokens)} to {len(truncated_tokens)} tokens")
        return truncated_text

    @classmethod
    def truncate_texts_batch(cls, 
                          texts: List[str], 
                          model: str = "text-embedding-3-large",
                          max_tokens: Optional[int] = None) -> List[str]:
        """
        Truncate multiple texts to fit within the token limit.
        
        Args:
            texts: List of texts to truncate
            model: The model to use for token counting
            max_tokens: Optional custom token limit, defaults to model's limit
            
        Returns:
            List[str]: The truncated texts
        """
        return [cls.truncate_text_to_token_limit(text, model, max_tokens) for text in texts]
        
    @classmethod
    def get_token_limit(cls, model: str) -> int:
        """
        Get the token limit for the specified model.
        
        Args:
            model: The model to get the token limit for
            
        Returns:
            int: The token limit for the model
        """
        return cls._token_limits.get(model, 8191)  # Default to 8191 if not specified


# Create a global instance for easy access
token_counter = OpenAITokenCounter()

def truncate_for_embeddings(text: str, model: str = "text-embedding-3-large") -> str:
    """
    Convenient function to truncate text for embeddings.
    
    Args:
        text: The text to truncate
        model: The embedding model to use
        
    Returns:
        str: The truncated text
    """
    return token_counter.truncate_text_to_token_limit(text, model)
    
def count_tokens(text: str, model: str = "text-embedding-3-large") -> int:
    """
    Convenient function to count tokens.
    
    Args:
        text: The text to count tokens for
        model: The model to use for token counting
        
    Returns:
        int: The number of tokens in the text
    """
    return token_counter.count_tokens(text, model)

def truncate_texts_batch(texts: List[str], model: str = "text-embedding-3-large") -> List[str]:
    """
    Convenient function to truncate multiple texts for embeddings.
    
    Args:
        texts: List of texts to truncate
        model: The embedding model to use
        
    Returns:
        List[str]: The truncated texts
    """
    return token_counter.truncate_texts_batch(texts, model)

def count_tokens_batch(texts: List[str], model: str = "text-embedding-3-large") -> List[int]:
    """
    Convenient function to count tokens for multiple texts.
    
    Args:
        texts: List of texts to count tokens for
        model: The model to use for token counting
        
    Returns:
        List[int]: The number of tokens in each text
    """
    return token_counter.count_tokens_batch(texts, model) 