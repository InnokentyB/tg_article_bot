#!/usr/bin/env python3
"""
Script to run the secure API server with HTTPS
"""
import os
import sys
import logging
import uvicorn
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_ssl_certificates():
    """Check if SSL certificates exist"""
    ssl_dir = Path("ssl")
    key_file = ssl_dir / "key.pem"
    cert_file = ssl_dir / "cert.pem"
    
    if not key_file.exists() or not cert_file.exists():
        logger.error("SSL certificates not found!")
        logger.info("Please run: ./generate_ssl.sh")
        return False
    
    logger.info("SSL certificates found")
    return True

def check_environment():
    """Check required environment variables"""
    required_vars = [
        "JWT_SECRET_KEY",
        "API_KEY",
        "DATABASE_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Please set them in your .env file")
        return False
    
    logger.info("Environment variables configured")
    return True

def main():
    """Main function"""
    logger.info("🔐 Starting Secure API Server...")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check SSL certificates
    if not check_ssl_certificates():
        sys.exit(1)
    
    # Import the secure app
    try:
        from api_server_secure import app
        logger.info("✅ Secure API server imported successfully")
    except ImportError as e:
        logger.error(f"Failed to import secure API server: {e}")
        sys.exit(1)
    
    # Get configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    ssl_keyfile = "ssl/key.pem"
    ssl_certfile = "ssl/cert.pem"
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    logger.info(f"🔒 SSL enabled: {ssl_certfile}")
    
    # Start server
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
