import aiohttp
import feedparser
import re
import asyncio
from datetime import datetime, timezone
from config import MIN_TITLE_LENGTH
from database import get_rss_cache, set_rss_cache

async def fetch_rss_with_etag(url: str) -> tuple:
    """Загрузка RSS с поддержкой ETag"""
    
    etag, last_modified = await get_rss_cache(url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/rss+xml, application/xml, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    if etag:
        headers['If-None-Match'] = etag
    if last_modified:
        headers['If-Modified-Since'] = last_modified
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 304:
                    return None, False
                
                new_etag = response.headers.get('ETag')
                new_modified = response.headers.get('Last-Modified')
                
                await set_rss_cache(url, new_etag, new_modified)
                
                content = await response.text()
                return content, True
                
    except Exception as e:
        print(f"⚠️ Ошибка загрузки {url}: {e}")
        return None, False

def check_keywords(text: str, keywords: str) -> bool:
    """Проверка ключевых слов"""
    if not text or not keywords:
        return False
    text_lower = text.lower()
    return any(kw.lower().strip() in text_lower for kw in keywords.split(','))

def clean_html(text: str) -> str:
    """Очистка от HTML"""
    if not text:
        return ''
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_date(date_str: str) -> datetime:
    """Парсинг даты"""
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        parsed = feedparser.util.parse_date(date_str)
        return parsed if parsed else datetime.now(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

async def parse_rss_source(source, user_id: int = None) -> list:
    """Парсинг одного источника"""
    articles = []
    
    rss_url = source.rss_url
    keywords = source.keywords or ''
    source_lang = source.lang or 'ru'
    source_name = source.name
    
    if not rss_url:
        return articles
    
    content, changed = await fetch_rss_with_etag(rss_url)
    
    if not changed or content is None:
        return articles
    
    try:
        feed = feedparser.parse(content)
        
        if feed.bozo and not feed.entries:
            return articles
        
        for entry in feed.entries[:15]:
            try:
                title = clean_html(entry.get('title') or '').strip()
                link = entry.get('link') or ''
                
                if isinstance(link, dict):
                    link = link.get('href', '')
                link = link.strip()
                
                if not title or not link or len(title) < MIN_TITLE_LENGTH:
                    continue
                
                # Поиск изображения
                image_url = None
                
                # 1. Проверяем media_content
                if 'media_content' in entry and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get('url')
                
                # 2. Проверяем enclosure
                if not image_url and 'links' in entry:
                    for link in entry.links:
                        if link.get('rel') == 'enclosure' and link.get('type', '').startswith('image/'):
                            image_url = link.get('href')
                            break
                            
                # 3. Ищем <img> в summary/content
                summary_raw = entry.get('summary') or entry.get('description') or entry.get('content', [{}])[0].get('value') or ''
                if not image_url and '<img' in summary_raw:
                    img_match = re.search(r'<img[^>]+src="([^">]+)"', summary_raw)
                    if img_match:
                        image_url = img_match.group(1)

                summary = clean_html(summary_raw)
                
                published = entry.get('published') or entry.get('updated') or ''
                pub_date = parse_date(published)
                
                text_to_check = f"{title} {summary}".lower()
                if not check_keywords(text_to_check, keywords):
                    continue
                
                articles.append({
                    'title': title,
                    'url': link,
                    'source': source_name,
                    'lang': source_lang,
                    'published': pub_date,
                    'summary': summary[:200] + '...' if len(summary) > 200 else summary,
                    'image_url': image_url
                })
                
            except Exception:
                continue
        
    except Exception as e:
        print(f"❌ Ошибка парсинга {source_name}: {e}")
    
    return articles

async def parse_all_for_user(user_id: int) -> list:
    """Парсинг всех источников пользователя"""
    from database import get_active_sources
    
    sources = await get_active_sources(user_id)
    
    if not sources:
        return []
    
    tasks = [parse_rss_source(source, user_id) for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)
    
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    
    seen = set()
    unique = []
    for article in all_articles:
        if article['url'] not in seen:
            seen.add(article['url'])
            unique.append(article)
    
    return unique