import os
from dotenv import load_dotenv

load_dotenv()

# ===========================
# 🔑 Telegram Bot Settings
# ===========================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')  # Основной канал для публикаций
ADMIN_ID = os.getenv('ADMIN_ID')      # Твой личный ID (куда слать черновики)

# ===========================
# 🤖 AI Provider: Groq
# ===========================
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')

# ===========================
# 🗄️ Database
# ===========================
DB_NAME = 'content_bot.db'

# ===========================
# 📰 RSS Sources
# ===========================
RSS_SOURCES = [
    {
        'name': 'xakep_ai',
        'rss': 'https://xakep.ru/tag/iskusstvennyj-intellekt/feed/',
        'keywords': ['искусственный интеллект', 'нейросеть', 'машинное обучение', 'безопасность'],
        'enabled': True,
        'lang': 'ru',
        'priority': 'high'
    },
    {
        'name': 'techcrunch_ai',
        'rss': 'https://techcrunch.com/category/artificial-intelligence/feed/',
        'keywords': ['ai startup', 'funding', 'generative ai', 'llm', 'venture', 'openai'],
        'enabled': True,
        'lang': 'en',
        'priority': 'high'
    },
    {
        'name': 'venturebeat_ai',
        'rss': 'https://venturebeat.com/category/ai/feed/',
        'keywords': ['artificial intelligence', 'enterprise ai', 'machine learning', 'automation'],
        'enabled': True,
        'lang': 'en',
        'priority': 'high'
    },
    {
        'name': 'arxiv_cs_ai',
        'rss': 'http://export.arxiv.org/rss/cs.AI',
        'keywords': ['artificial intelligence', 'machine learning', 'neural', 'llm', 'research'],
        'enabled': True,
        'lang': 'en',
        'priority': 'low'
    },
    {
        'name': 'google_ai_blog',
        'rss': 'https://blog.google/technology/ai/rss/',
        'keywords': ['gemini', 'ai', 'model', 'research', 'google ai', 'deepmind'],
        'enabled': True,
        'lang': 'en',
        'priority': 'high'
    },
    {
        'name': 'microsoft_ai',
        'rss': 'https://blogs.microsoft.com/ai/feed/',
        'keywords': ['copilot', 'azure ai', 'openai', 'enterprise', 'ai tools'],
        'enabled': True,
        'lang': 'en',
        'priority': 'medium'
    }
]

# ===========================
# 🔍 Глобальные ключевые слова
# ===========================
ALL_KEYWORDS = [
    'нейросеть', 'искусственный интеллект', 'иИ', 'машинное обучение',
    'gpt', 'llm', 'генеративный', 'автоматизация', 'ai', 'artificial intelligence',
    'machine learning', 'deep learning', 'neural network', 'transformer'
]

# ===========================
# ⏱️ Scheduler Settings (5-6 часов)
# ===========================
POSTS_PER_DAY = 4
POST_INTERVAL_MIN = 300  # 5 часов
POST_INTERVAL_MAX = 360  # 6 часов

# ===========================
# 🎯 Content Settings
# ===========================
MIN_TITLE_LENGTH = 15

POST_STYLES = ['factual', 'analytical', 'practical', 'news', 'question']

STYLE_EMOJIS = {
    'factual': '📊',
    'analytical': '🔍',
    'practical': '🛠️',
    'news': '⚡',
    'question': '❓'
}