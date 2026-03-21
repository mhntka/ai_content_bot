import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from ai_writer import generate_post


@pytest.mark.asyncio
@patch("ai_writer.GROQ_API_KEY", "fake_key")
async def test_generate_post_groq_success():
    """Тест успешной генерации поста через Groq"""
    with patch("groq.AsyncGroq") as mock_groq_class:
        mock_client = mock_groq_class.return_value
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Test post content\n\n📌 Test title"
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await generate_post(
            title="Test Title",
            source_url="http://test.com",
            lang="ru",
            summary="Test summary",
            source_name="Test Source",
            ai_provider="groq",
        )

        assert result["success"] is True, f"Failed with error: {result['error']}"
        assert "Test post content" in result["text"]
        assert result["error"] is None


@pytest.mark.asyncio
@patch("ai_writer.OPENAI_API_KEY", "fake_key")
async def test_generate_post_openai_success():
    """Тест успешной генерации поста через OpenAI"""
    with patch("openai.AsyncOpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "OpenAI test content"
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await generate_post(
            title="Test Title",
            source_url="http://test.com",
            lang="ru",
            summary="Test summary",
            source_name="Test Source",
            ai_provider="openai",
        )

        assert result["success"] is True, f"Failed with error: {result['error']}"
        assert "OpenAI test content" in result["text"]
        assert result["error"] is None


@pytest.mark.asyncio
@patch("ai_writer.ANTHROPIC_API_KEY", "fake_key")
async def test_generate_post_anthropic_success():
    """Тест успешной генерации поста через Anthropic"""
    with patch("anthropic.AsyncAnthropic") as mock_anthropic_class:
        mock_client = mock_anthropic_class.return_value
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Anthropic test content"
        mock_response.content = [mock_content]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        result = await generate_post(
            title="Test Title",
            source_url="http://test.com",
            lang="ru",
            summary="Test summary",
            source_name="Test Source",
            ai_provider="anthropic",
        )

        assert result["success"] is True, f"Failed with error: {result['error']}"
        assert "Anthropic test content" in result["text"]
        assert result["error"] is None


@pytest.mark.asyncio
@patch("ai_writer.GROQ_API_KEY", "fake_key")
async def test_generate_post_failure():
    """Тест обработки ошибки при генерации"""
    with patch("groq.AsyncGroq") as mock_groq_class:
        mock_client = mock_groq_class.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await generate_post(
            title="Test Title", source_url="http://test.com", ai_provider="groq"
        )

        assert result["success"] is False
        assert result["text"] is None
        assert "API Error" in result["error"]
