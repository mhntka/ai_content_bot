import random
import re
from groq import AsyncGroq
from config import GROQ_API_KEY, GROQ_MODEL, POST_STYLES, STYLE_EMOJIS

client = AsyncGroq(api_key=GROQ_API_KEY)

def get_random_style() -> tuple[str, str]:
    """Случайный стиль поста + эмодзи"""
    style = random.choice(POST_STYLES)
    emoji = STYLE_EMOJIS.get(style, '📌')
    return style, emoji

async def generate_post(
    title: str, 
    source_url: str, 
    lang: str = 'en', 
    summary: str = '',
    source_name: str = ''
) -> dict:
    """
    Генерация поста с ротацией стилей для разнообразия.
    """
    style, emoji = get_random_style()
    
    # Инструкции в зависимости от стиля
    style_instructions = {
        'factual': 'Пиши кратко, только факты и цифры. Без оценок.',
        'analytical': 'Добавь анализ: почему это произошло, какие последствия.',
        'practical': 'Сделай акцент на пользе: как это использовать, что даст читателю.',
        'news': 'Пиши как срочную новость: что, где, когда. Динамично.',
        'question': 'Закончи пост вопросом к аудитории для вовлечения.'
    }
    
    # Инструкции для английских статей
    if lang == 'en':
        lang_block = """
📌 СТАТЬЯ НА АНГЛИЙСКОМ:
• Переведи заголовок на русский, адаптируй для РФ/СНГ
• Выдели 1-2 ключевых факта
• Объясни, почему это важно для нас
• Пиши пост ПОЛНОСТЬЮ на русском
"""
    else:
        lang_block = ""
    
    # Источник для контекста
    source_note = f"Источник: {source_name}. " if source_name else ""
    
    prompt = f"""
Ты — профессиональный контент-менеджер Telegram-канала про ИИ.

{lang_block}
СТИЛЬ ПОСТА: {style} ({style_instructions[style]})
{source_note}
ЗАГОЛОВОК: {title}
СУТЬ: {summary[:150] if summary else 'Нет дополнительной информации'}

ПРАВИЛА:
✅ Заголовок: **жирным**, 8-12 слов, цепляющий, на русском
✅ Суть: 2-3 коротких предложения, только факты
✅ Важно: 1 предложение — конкретная выгода или инсайт
✅ Хэштеги: 3-4 коротких, на русском, без пробелов
✅ Эмодзи: 1-2 шт, только в начале разделов
✅ Язык: русский, живой, без канцелярита и воды

❌ ЗАПРЕЩЕНО:
- "уникальный", "инновационный", "стремительно", "в мире технологий"
- Повторы, общие фразы, клише
- Хэштеги длиннее 15 символов
- Дословный перевод — адаптируй смысл

ФОРМАТ (строго):
{emoji} **Адаптированный заголовок**

📌 Краткая суть...

🎯 Почему это важно...

#ИИ #нейросети #технологии
"""
    
    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.65,  # Баланс креатива и точности
            max_tokens=550
        )
        
        text = response.choices[0].message.content.strip()
        
        # Пост-обработка
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return {'text': text, 'success': True, 'error': None, 'style': style}
        
    except Exception as e:
        return {'text': None, 'success': False, 'error': str(e), 'style': style}


async def generate_digest(articles: list) -> str:
    """Генерация недельного дайджеста"""
    
    titles = "\n".join([f"- {a['title']}" for a in articles[:5]])
    
    prompt = f"""
Сделай дайджест из новостей за неделю:

{titles}

Формат:
🗞️ Вступление (1 предложение — общий тренд)
📰 По 1 предложению на новость (факты)
🎯 Итог: что запомнилось / что ждать дальше

Стиль: кратко, с эмодзи, без воды.
"""
    
    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=650
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Ошибка: {e}"