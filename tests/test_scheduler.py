import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from scheduler import fetch_unsplash_image, publish_for_channel
import scheduler

@pytest.mark.asyncio
@patch('scheduler.os.getenv', return_value='test_api_key')
@patch('aiohttp.ClientSession.get')
async def test_fetch_unsplash_image_success(mock_get, mock_getenv):
    """Тест успешного получения картинки из Unsplash"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={'urls': {'regular': 'http://unsplash.com/image.jpg'}})
    
    mock_get.return_value.__aenter__.return_value = mock_response

    url = await fetch_unsplash_image("ai")
    assert url == 'http://unsplash.com/image.jpg'

@pytest.mark.asyncio
@patch('scheduler.os.getenv', return_value='test_api_key')
@patch('aiohttp.ClientSession.get')
async def test_fetch_unsplash_image_not_found(mock_get, mock_getenv):
    """Тест когда картинка не найдена или ошибка API"""
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_get.return_value.__aenter__.return_value = mock_response

    url = await fetch_unsplash_image("invalid_query")
    assert url is None

@pytest.mark.asyncio
@patch('scheduler.os.getenv', return_value=None)
async def test_fetch_unsplash_image_no_key(mock_getenv):
    """Тест когда нет ключа API"""
    url = await fetch_unsplash_image("ai")
    assert url is None
