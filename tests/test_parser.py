import pytest
from unittest.mock import patch, MagicMock
from parser import parse_rss_source, check_keywords, clean_html


@pytest.fixture
def mock_source():
    source = MagicMock()
    source.rss_url = "http://test.com/rss"
    source.keywords = "ai, test"
    source.lang = "en"
    source.name = "Test Source"
    return source


def test_check_keywords():
    """Тест проверки ключевых слов"""
    text = "This is an article about AI and machine learning"
    assert check_keywords(text, "ai, test") is True
    assert check_keywords(text, "robot, space") is False
    assert check_keywords(text, "MACHINE LEARNING") is True


def test_clean_html():
    """Тест очистки HTML"""
    html_text = "<p>This is a <b>test</b>.</p>"
    assert clean_html(html_text) == "This is a test."

    html_text2 = "<div>Some text   with \n spaces</div>"
    assert clean_html(html_text2) == "Some text with spaces"


@pytest.mark.asyncio
@patch("parser.fetch_rss_with_etag")
async def test_parse_rss_source_image_extraction_media_content(mock_fetch, mock_source):
    """Тест извлечения картинки из media_content"""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
      <channel>
        <title>Test Channel</title>
        <item>
          <title>AI Test Article</title>
          <link>http://test.com/article1</link>
          <description>This is a test summary about AI.</description>
          <media:content url="http://test.com/image1.jpg" type="image/jpeg" />
        </item>
      </channel>
    </rss>
    """
    mock_fetch.return_value = (rss_xml, True)

    articles = await parse_rss_source(mock_source)
    assert len(articles) == 1
    assert articles[0]["title"] == "AI Test Article"
    assert articles[0]["image_url"] == "http://test.com/image1.jpg"


@pytest.mark.asyncio
@patch("parser.fetch_rss_with_etag")
async def test_parse_rss_source_image_extraction_enclosure(mock_fetch, mock_source):
    """Тест извлечения картинки из enclosure"""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Test Channel</title>
        <item>
          <title>Another AI Article</title>
          <link>http://test.com/article2</link>
          <description>Summary about artificial intelligence.</description>
          <enclosure url="http://test.com/image2.png" type="image/png" length="10000" />
        </item>
      </channel>
    </rss>
    """
    mock_fetch.return_value = (rss_xml, True)

    articles = await parse_rss_source(mock_source)
    assert len(articles) == 1
    assert articles[0]["image_url"] == "http://test.com/image2.png"


@pytest.mark.asyncio
@patch("parser.fetch_rss_with_etag")
async def test_parse_rss_source_image_extraction_img_tag(mock_fetch, mock_source):
    """Тест извлечения картинки из тега img в описании"""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Test Channel</title>
        <item>
          <title>AI and Images Test</title>
          <link>http://test.com/article3</link>
          <description>&lt;img src="http://test.com/image3.webp"&gt; This is an AI test.</description>
        </item>
      </channel>
    </rss>
    """
    mock_fetch.return_value = (rss_xml, True)

    articles = await parse_rss_source(mock_source)
    assert len(articles) == 1
    assert articles[0]["image_url"] == "http://test.com/image3.webp"
    # Описание должно быть очищено от HTML
    assert articles[0]["summary"] == "This is an AI test."


@pytest.mark.asyncio
@patch("parser.fetch_rss_with_etag")
async def test_parse_rss_source_no_keywords(mock_fetch, mock_source):
    """Тест фильтрации по ключевым словам"""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Test Channel</title>
        <item>
          <title>Dogs are cute</title>
          <link>http://test.com/article4</link>
          <description>Just an article about dogs.</description>
        </item>
      </channel>
    </rss>
    """
    mock_fetch.return_value = (rss_xml, True)

    articles = await parse_rss_source(mock_source)
    # Статья не содержит "ai" или "test" в заголовке или тексте (после lowercasing)
    assert len(articles) == 0
