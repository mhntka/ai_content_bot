import aiohttp
import feedparser
import re
from datetime import datetime, timezone
from config import RSS_SOURCES, ALL_KEYWORDS, MIN_TITLE_LENGTH


async def fetch_rss(url: str) -> str:
    """
    Загрузка RSS-ленты с заголовками для обхода базовых блокировок.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.google.com/',
                'Connection': 'keep-alive',
            },
            timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
            response.raise_for_status()
            return await response.text()


def check_keywords(text: str, keywords: list) -> bool:
    """
    Проверка наличия хотя бы одного ключевого слова в тексте.
    """
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def clean_html(text: str) -> str:
    """
    Удаление HTML-тегов и лишних пробелов из текста.
    """
    if not text:
        return ''
    # Удаляем теги
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    # Нормализуем пробелы и переносы
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_date(date_str: str) -> datetime:
    """
    Парсинг даты из RSS в объект datetime.
    """
    if not date_str:
        return datetime.now(timezone.utc)
    
    # feedparser уже парсит даты, но на всякий случай
    try:
        parsed = feedparser.util.parse_date(date_str)
        if parsed:
            return parsed
    except:
        pass
    
    # fallback
    return datetime.now(timezone.utc)


async def parse_rss_source(source: dict) -> list:
    """
    Парсинг одного RSS-источника.
    Возвращает список статей, соответствующих ключевым словам.
    """
    articles = []
    
    if not source.get('enabled', True):
        return articles
    
    source_name = source.get('name', 'unknown')
    rss_url = source.get('rss', '')
    keywords = (source.get('keywords', []) or []) + ALL_KEYWORDS
    source_lang = source.get('lang', 'en')
    
    if not rss_url:
        print(f"⚠️ {source_name}: нет RSS-ссылки")
        return articles
    
    try:
        print(f"🔍 Загружаю {source_name}...")
        rss_content = await fetch_rss(rss_url)
        feed = feedparser.parse(rss_content)
        
        # Проверка на ошибки парсинга
        if feed.bozo and not feed.entries:
            print(f"⚠️ {source_name}: ошибка парсинга RSS (bozo={feed.bozo})")
            return articles
        
        if not feed.entries:
            print(f"⚠️ {source_name}: нет записей в фиде")
            return articles
        
        found_count = 0
        
        for entry in feed.entries[:20]:  # Берём последние 20 записей для фильтрации
            try:
                # Извлекаем поля
                title = entry.get('title') or entry.get('dc_title', '')
                title = clean_html(title).strip()
                
                link = entry.get('link') or entry.get('guid', '')
                if isinstance(link, dict):
                    link = link.get('href', '')
                link = link.strip()
                
                # Пропускаем пустые
                if not title or not link:
                    continue
                if len(title) < MIN_TITLE_LENGTH:
                    continue
                
                # Краткое описание (для фильтрации и контекста)
                summary = clean_html(
                    entry.get('summary') or 
                    entry.get('description') or 
                    entry.get('content', [{}])[0].get('value') or 
                    ''
                )
                
                # Дата публикации
                published = entry.get('published') or entry.get('updated') or ''
                pub_date = parse_date(published)
                
                # Проверка по ключевым словам (заголовок + описание)
                text_to_check = f"{title} {summary}".lower()
                if not check_keywords(text_to_check, keywords):
                    continue
                
                # Избегаем дублей внутри одного источника
                if any(a['url'] == link for a in articles):
                    continue
                
                found_count += 1
                articles.append({
                    'title': title,
                    'url': link,
                    'source': source_name,
                    'lang': source_lang,
                    'published': pub_date,
                    'summary': summary[:200] + '...' if len(summary) > 200 else summary
                })
                
            except Exception as e:
                # Пропускаем проблемные записи, не останавливаем весь парсинг
                continue
        
        print(f"✅ {source_name}: найдено {found_count} релевантных статей")
        
    except aiohttp.ClientError as e:
        print(f"❌ {source_name}: сетевая ошибка — {e}")
    except feedparser.FeedParserError as e:
        print(f"❌ {source_name}: ошибка парсинга XML — {e}")
    except Exception as e:
        print(f"❌ {source_name}: непредвиденная ошибка — {type(e).__name__}: {e}")
    
    return articles


async def parse_all() -> list:
    """
    Парсинг всех включённых источников.
    Возвращает отсортированный список уникальных статей.
    """
    all_articles = []
    
    # Парсим источники последовательно (чтобы не перегружать сеть)
    for source in RSS_SOURCES:
        articles = await parse_rss_source(source)
        all_articles.extend(articles)
    
    if not all_articles:
        print("⚠️ Ни один источник не вернул статьи")
        return []
    
    # Сортируем по дате: сначала новые
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    
    # Убираем дубликаты по URL (глобально)
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article['url'] not in seen_urls:
            seen_urls.add(article['url'])
            unique_articles.append(article)
    
    print(f"\n🎯 Всего уникальных статей после фильтрации: {len(unique_articles)}")
    return unique_articles