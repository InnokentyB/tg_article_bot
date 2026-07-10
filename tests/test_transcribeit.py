import asyncio
import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from aiogram.types import Message, CallbackQuery, Chat, User
from database import DatabaseManager
from telegram_bot import ArticleBot
from transcribeit_client import TranscribeItClient

# Mock active database to avoid network requests on real DB where possible
@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock(spec=DatabaseManager)
    db.save_article = AsyncMock(return_value=(123, "mock-fingerprint"))
    db.update_article_categories = AsyncMock()
    return db

@pytest.fixture
def bot(mock_db) -> ArticleBot:
    # Set dummy token so aiogram doesn't fail init
    os.environ["ARTICLE_BOT_TOKEN"] = "123456789:AABBCCDDEEFFgg"
    os.environ["TRANSCRIBEIT_API_KEY"] = "sk_test_transcribeit_key"
    os.environ["TRANSCRIBEIT_API_URL"] = "https://www.transcribeit.ru"
    
    bot_inst = ArticleBot()
    bot_inst.db = mock_db
    return bot_inst


def test_is_video_url(bot: ArticleBot) -> None:
    """Test video URL pattern matching"""
    assert bot.is_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert bot.is_video_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert bot.is_video_url("https://rutube.ru/video/12345/") is True
    assert bot.is_video_url("https://vk.com/video-123_456") is True
    assert bot.is_video_url("https://vkvideo.ru/video123_456") is True
    assert bot.is_video_url("https://habr.com/ru/post/12345/") is False
    assert bot.is_video_url("https://vk.com/some_profile") is False


@pytest.mark.asyncio
async def test_transcribeit_client_upload_success() -> None:
    """Test successful file upload via TranscribeItClient"""
    client = TranscribeItClient(api_key="test_key", base_url="https://test.transcribeit.ru")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={"transaction_id": "test-uuid-12345", "status": "processing"})
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        tx_id = await client.upload_file(b"raw-audio-data", "audio.mp3", language="ru")
        assert tx_id == "test-uuid-12345"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_transcribeit_client_get_transcription() -> None:
    """Test polling transcription status via TranscribeItClient"""
    client = TranscribeItClient(api_key="test_key", base_url="https://test.transcribeit.ru")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={"status": "completed", "text": "Hello world transcription"})
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await client.get_transcription("test-uuid-12345")
        assert result is not None
        assert result["status"] == "completed"
        assert result["text"] == "Hello world transcription"


@pytest.mark.asyncio
async def test_suggest_video_url_transcription(bot: ArticleBot) -> None:
    """Verify that message with video link triggers transcription suggestions"""
    chat = Chat(id=111, type="private")
    user = User(id=222, is_bot=False, first_name="Test")
    message = Message(
        message_id=999,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    
    with patch("aiogram.types.Message.answer", new_callable=AsyncMock) as mock_answer:
        state = AsyncMock()
        state.get_state = AsyncMock(return_value=None)
        await bot.process_message(message, state=state)
        mock_answer.assert_called_once()
        args, kwargs = mock_answer.call_args
        assert "Обнаружена ссылка на видео!" in args[0]
        assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_start_transcription_polling_success(bot: ArticleBot) -> None:
    """Verify transcription polling loop and DB ingestion flow"""
    # Mock api response to return 'completed' on first request
    mock_result = {"status": "completed", "text": "This is the transcript of the video."}
    
    with patch.object(bot.transcribeit_client, "get_transcription", new_callable=AsyncMock, return_value=mock_result):
        with patch.object(bot.bot, "edit_message_text", new_callable=AsyncMock) as mock_edit:
            await bot.start_transcription_polling(
                transaction_id="mock-tx-id",
                chat_id=111,
                message_id=999,
                original_link="youtube_link",
                title="Test Video",
                user_id=222
            )
            
            # Check database calls
            bot.db.save_article.assert_called_once()
            bot.db.update_article_categories.assert_called_once()
            
            # Check success message edited
            mock_edit.assert_called_once()
            args, kwargs = mock_edit.call_args
            assert "Транскрибация завершена!" in kwargs.get("text", "")
