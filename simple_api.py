"""
Simple version to test just the API server
"""
import logging
import os
import uvicorn
from api_server import app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting API server...")
    
    # Check required environment variables
    if not os.getenv('DATABASE_URL'):
        logger.error("DATABASE_URL environment variable is required")
        exit(1)
    
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")