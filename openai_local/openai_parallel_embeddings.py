import asyncio
import time
import logging
from openai import OpenAI
from typing import List
from openai_local.openai_rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

async def process_embeddings_in_parallel(texts: List[str], model: str, api_key: str):
    """
    Process embedding requests in parallel with centralized rate limiting.
    Returns a list of embeddings in the same order as input texts.
    """
    logger.info(f"Starting parallel embedding generation for {len(texts)} texts")
    client = OpenAI(api_key=api_key)
    results = [None] * len(texts)
    
    # Use a semaphore to control concurrency - 20 concurrent requests max
    semaphore = asyncio.Semaphore(20)
    
    async def get_embedding(idx, text):
        # Use centralized rate limiter with token count
        token_count = len(text)  # Simple approximation of token count
        await asyncio.to_thread(rate_limiter.check_and_wait, token_count)
        
        # Use the semaphore to limit concurrent requests
        async with semaphore:
            try:
                response = client.embeddings.create(model=model, input=text)
                results[idx] = response.data[0].embedding
            except Exception as e:
                logger.warning(f"Error generating embedding for item {idx}: {e}")
                # Simple retry for rate limit errors
                if "rate limit" in str(e).lower() or "429" in str(e):
                    await asyncio.sleep(2)  # Wait before retrying
                    try:
                        # Try again with rate limiting
                        await asyncio.to_thread(rate_limiter.check_and_wait, token_count)
                        response = client.embeddings.create(model=model, input=text)
                        results[idx] = response.data[0].embedding
                    except Exception as retry_e:
                        logger.error(f"Failed on retry for item {idx}: {retry_e}")
    
    # Create tasks for all embeddings
    tasks = [get_embedding(i, text) for i, text in enumerate(texts)]
    
    # Run all tasks concurrently
    await asyncio.gather(*tasks)
    
    # Count successful embeddings
    success_count = sum(1 for r in results if r is not None)
    logger.info(f"Completed parallel embedding generation: {success_count}/{len(texts)} successful")
    
    return results 