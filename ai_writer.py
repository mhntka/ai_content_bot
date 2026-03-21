import random
import re
import groq
import openai
import anthropic
from config import (
    POST_STYLES,
    STYLE_EMOJIS,
    GROQ_API_KEY,
    GROQ_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
)


def get_random_style() -> tuple:
    """Случайный стиль"""
    style = random.choice(POST_STYLES)
    emoji = STYLE_EMOJIS.get(style, "📌")
    return style, emoji


async def generate_post(
    title: str,
    source_url: str,
    lang: str = "en",
    summary: str = "",
    source_name: str = "",
    ai_provider: str = "groq",
    custom_prompt: str = None,
) -> dict:
    """Генерация поста"""

    style, emoji = get_random_style()

    style_instructions = {
        "factual": "Пиши кратко, только факты.",
        "analytical": "Добавь анализ и последствия.",
        "practical": "Сделай акцент на пользе.",
        "news": "Пиши как срочную новость.",
        "question": "Закончи вопросом к аудитории.",
    }

    if lang == "en":
        lang_block = "📌 Переведи на русский и адаптируй.\n"
    else:
        lang_block = ""

    if custom_prompt:
        user_prompt_block = f"ИНДИВИДУАЛЬНЫЕ ПРАВИЛА КАНАЛА:\n{custom_prompt}\n"
    else:
        user_prompt_block = ""

    prompt = f"""
Ты — контент-менеджер Telegram-канала про ИИ.

{lang_block}
СТИЛЬ: {style} ({style_instructions[style]})
ИСТОЧНИК: {source_name}
{user_prompt_block}
ЗАГОЛОВОК: {title}
СУТЬ: {summary[:150] if summary else "Нет доп. информации"}

ПРАВИЛА:
✅ Заголовок: **жирным**, 8-12 слов
✅ Суть: 2-3 предложения
✅ Важно: 1 предложение
✅ Хэштеги: 3-4 коротких
✅ Эмодзи: 1-2 шт

❌ ЗАПРЕЩЕНО:
- "уникальный", "инновационный"
- Повторы, вода

ФОРМАТ:
{emoji} **Заголовок**

📌 Суть...

🎯 Почему важно...

#ИИ #нейросети #технологии
"""

    try:
        text = ""
        if ai_provider == "openai":
            client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Ты — контент-менеджер."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.65,
                max_tokens=550,
            )
            text = response.choices[0].message.content.strip()

        elif ai_provider == "anthropic":
            client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            response = await client.messages.create(
                model=ANTHROPIC_MODEL,
                system="Ты — контент-менеджер.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.65,
                max_tokens=550,
            )
            text = response.content[0].text.strip()

        else:  # default groq
            client = groq.AsyncGroq(api_key=GROQ_API_KEY)
            response = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Ты — контент-менеджер."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.65,
                max_tokens=550,
            )
            text = response.choices[0].message.content.strip()

        text = re.sub(r"\n{3,}", "\n\n", text)

        return {"text": text, "success": True, "error": None, "style": style}

    except Exception as e:
        return {"text": None, "success": False, "error": str(e), "style": style}
