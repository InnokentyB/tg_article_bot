"""
API client for TranscribeIt.ru transcription service
"""
import logging
from typing import Optional, Dict, Any, Union
import httpx

logger = logging.getLogger(__name__)

class TranscribeItClient:
    """Client for TranscribeIt.ru API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        """
        Initialize the TranscribeIt client.
        
        :param api_key: TranscribeIt API Key (X-API-Key header value)
        :param base_url: TranscribeIt API base URL (defaults to https://www.transcribeit.ru)
        """
        import os
        self.api_key: Optional[str] = api_key or os.getenv("TRANSCRIBEIT_API_KEY")
        raw_url: str = base_url or os.getenv("TRANSCRIBEIT_API_URL", "https://www.transcribeit.ru")
        # Strip trailing slash from base url
        self.base_url: str = raw_url.rstrip("/")
        
    def is_configured(self) -> bool:
        """
        Check if the client has an API key configured.
        
        :return: True if api_key is set, False otherwise
        """
        return bool(self.api_key)

    async def upload_file(
        self, 
        file_path_or_data: Union[str, bytes], 
        filename: str, 
        language: str = "ru"
    ) -> Optional[str]:
        """
        Upload audio or video file to TranscribeIt.ru.
        
        :param file_path_or_data: File path on disk or raw bytes content
        :param filename: Filename for the content
        :param language: Language code (e.g. 'ru', 'en', 'auto')
        :return: transaction_id (UUID string) if successful, None otherwise
        """
        if not self.api_key:
            logger.error("[TranscribeIt] Cannot upload: API key is not configured.")
            return None
            
        url: str = f"{self.base_url}/upload"
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key
        }
        
        # Prepare file content
        file_bytes: bytes
        if isinstance(file_path_or_data, str):
            try:
                with open(file_path_or_data, "rb") as f:
                    file_bytes = f.read()
            except Exception as e:
                logger.error(f"[TranscribeIt] Failed to read file {file_path_or_data}: {e}")
                return None
        else:
            file_bytes = file_path_or_data
            
        files = {
            "file": (filename, file_bytes)
        }
        data = {
            "language": language
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"[TranscribeIt] Uploading {filename} ({len(file_bytes)} bytes) to {url}...")
                response = await client.post(url, headers=headers, files=files, data=data)
                
                if response.status_code != 200:
                    logger.error(f"[TranscribeIt] Upload failed with status {response.status_code}: {response.text}")
                    return None
                    
                resp_json = response.json()
                transaction_id: Optional[str] = resp_json.get("transaction_id")
                logger.info(f"[TranscribeIt] File uploaded successfully. Transaction ID: {transaction_id}")
                return transaction_id
                
        except Exception as e:
            logger.error(f"[TranscribeIt] Error uploading file: {e}")
            return None

    async def get_transcription(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Check status/get text of transcription task by transaction_id.
        
        :param transaction_id: UUID transaction identifier
        :return: Dict containing status ('processing'/'completed'/'failed') and text if completed, or None on error
        """
        if not self.api_key:
            logger.error("[TranscribeIt] Cannot check status: API key is not configured.")
            return None
            
        url: str = f"{self.base_url}/transcriptions/{transaction_id}"
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"[TranscribeIt] Status check failed with status {response.status_code}: {response.text}")
                    return None
                    
                resp_json: Dict[str, Any] = response.json()
                return resp_json
                
        except Exception as e:
            logger.error(f"[TranscribeIt] Error checking transcription status for {transaction_id}: {e}")
            return None
