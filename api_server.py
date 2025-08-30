#!/usr/bin/env python3
"""
API Server для Railway (простая версия)
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Railway API",
    description="API for Railway deployment",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    """Root endpoint"""
    logger.info("Root endpoint called")
    return {
        "message": "Railway API is running!", 
        "status": "ok"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check called")
    return {
        "status": "healthy", 
        "service": "railway-api"
    }

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint for Railway"""
    logger.info("API health check called")
    return {
        "status": "healthy", 
        "service": "railway-api"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint"""
    logger.info("Test endpoint called")
    return {
        "message": "Test endpoint works!",
        "port": os.getenv("PORT", "not set")
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting Railway API server on port {port}")
    logger.info(f"Environment PORT: {os.getenv('PORT')}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
