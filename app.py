import os
import asyncio
import logging
import time
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Load ENV ──────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BREATHING_PAGE_URL = os.getenv("BREATHING_PAGE_URL", "https://yourusername.github.io/breathe")

OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "TelegramBot")

print(f"🤖 Bot starting... TELEGRAM_TOKEN: {'✅' if TELEGRAM_TOKEN else '❌'}")
print(f"🧠 OpenRouter key: {'✅' if OPENROUTER_API_KEY else '❌'}")

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _openrouter_headers() -> dict:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = OPENROUTER_SITE_URL
    if OPENROUTER_APP_NAME:
        headers["X-Title"] = OPENROUTER_APP_NAME
    return headers


# ── Auto-Fetch Free Models ────────────────────────────────────────
def fetch_free_models() -> list:
    """
    Calls OpenRouter API to get all currently available free models.
    """
    logger.info("🔄 Fetching live free models from OpenRouter...")
    try:
        resp = requests.get(OPENROUTER_MODELS_URL, headers=_openrouter_headers(), timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            free_models = []
            
            for m in data:
                pricing = m.get("pricing", {})
                # A model is free if prompt and completion price are both "0"
                if pricing.get("prompt") == "0" and pricing.get("completion") == "0":
                    free_models.append(m["id"])
            
            # Always put the OpenRouter auto-router first
            if "openrouter/free" not in free_models:
                free_models.insert(0, "openrouter/free")
            else:
                free_models.remove("openrouter/free")
                free_models.insert(0, "openrouter/free")
                
            logger.info(f"✅ Found {len(free_models)} free models.")
            return free_models
        else:
            logger.error(f"❌ Failed to fetch models: {resp.status_code}")
    except Exception as e:
        logger.error(f"❌ Error fetching models: {e}")
    
    # Safe fallback if API fails
    return ["openrouter/free", "liquid/lfm-2.5-1.2b-instruct:free", "google/gemma-3-27b-it:free"]

# Load them once at startup
MODEL_PRIORITY = fetch_free_models()
print(f"🧩 Loaded {len(MODEL_PRIORITY)} models to cycle through.")


SYSTEM_PROMPT = (
    "You are a compassionate mental health companion. "
    "Respond with empathy and warmth. Never diagnose. "
    "Recommend professional help for serious issues. "
    "Keep replies under 150 words."
)

# ── Session Storage ───────────────────────────────────────────────
chat_sessions = {}
HISTORY_PAIRS_TO_KEEP = 12 

# ── Crisis Keywords ───────────────────────────────────────────────
CRISIS_KEYWORDS = [
    "wanna die", "want to die", "kill myself", "end my life",
    "suicide", "suicidal", "self harm", "self-harm", "no reason to live",
    "can't go on", "cant go on", "better off dead", "end it all",
    "don't want to live", "dont want to live", "harm myself"
]

def is_crisis(text: str) -> bool:
    text_lower = (text or "").lower()
    return any(kw in text_lower for kw in CRISIS_KEYWORDS)

# ── Per-model failure tracker ─────────────────────────────────────
_model_state: dict = {}
MODEL_FAILURE_THRESHOLD = int(os.getenv("MODEL_FAILURE_THRESHOLD", "2"))
MODEL_COOLDOWN_SECONDS  = int(os.getenv("MODEL_COOLDOWN_SECONDS", "60"))

def _mark_model_failed(model: str):
    state = _model_state.setdefault(model, {"fails": 0, "skip_until": 0.0})
    state["fails"] += 1
    if state["fails"] >= MODEL_FAILURE_THRESHOLD:
        state["skip_until"] = time.time() + MODEL_COOLDOWN_SECONDS
        logger.warning(f"🚫 {model} cooled down for {MODEL_COOLDOWN_SECONDS}s.")

def _is_model_available(model: str) -> bool:
    state = _model_state.get(model)
    if state is None:
        return True
    if time.time() >= state["skip_until"]:
        state["fails"] = 0
        state["skip_until"] = 0.0
        return True
    return False

# ── Chat Sync & Async ─────────────────────────────────────────────
def _openrouter_chat_sync(messages, user_id: str, max_tokens: int, temperature: float) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY missing")

    tried = 0
    for model in MODEL_PRIORITY:
        if not _is_model_available(model):
            continue

        tried += 1
        payload = {
            "model":       model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
            "user":        user_id,
        }

        try:
            resp = requests.post(
                OPENROUTER_CHAT_URL,
                headers=_openrouter_headers(),
                json=payload,
                timeout=20,
            )

            if resp.status_code == 200:
                data = resp.json()
                content = ((data.get("choices", [{}])[0].get("message") or {}).get("content") or "")
                if content.strip():
                    if model in _model_state:
                        _model_state[model] = {"fails": 0, "skip_until": 0.0}
                    used_model = (data.get("model") or model)
                    logger.info(f"✅ Response from: {used_model}")
                    return content

            # 404 (Not Found), 429 (Rate Limit), or 5xx (Server Error) -> Skip model safely
            if resp.status_code in [404, 410, 429, 500, 502, 503, 504]:
                logger.warning(f"⚠️  {model} → HTTP {resp.status_code}. Skipping.")
                _mark_model_failed(model)
                continue

            # Auth Error
            if resp.status_code in [401, 403]:
                raise RuntimeError(f"OpenRouter Auth Error: {resp.text[:100]}")

            # Other unknown errors -> skip safely
            logger.warning(f"⚠️  {model} → HTTP {resp.status_code}. Body: {resp.text[:100]}")
            _mark_model_failed(model)
            continue

        except RuntimeError:
            raise
        except Exception as e:
            logger.warning(f"⚠️  {model} connection error: {e}. Trying next...")
            _mark_model_failed(model)
            continue

    raise RuntimeError(f"All {tried} available models failed or are in cooldown. Try again soon.")

async def openrouter_chat(messages, user_id: str, max_tokens: int = 220, temperature: float = 0.7) -> str:
    return await asyncio.to_thread(_openrouter_chat_sync, messages, user_id, max_tokens, temperature)


# ── Stress Rater ──────────────────────────────────────────────────
async def get_stress_level(user_text: str, user_id: str) -> int:
    prompt = (
        "You are a mental health triage assistant.\n"
        "Rate emotional distress 1-5. 5=crisis/self-harm. Reply ONLY with 1 digit.\n"
        f"Message: \"{user_text}\""
    )
    messages = [
        {"role": "system", "content": "You output only a single digit 1-5."},
        {"role": "user", "content": prompt},
    ]
    try:
        txt = await openrouter_chat(messages, user_id=user_id, max_tokens=3, temperature=0.0)
        raw = (txt or "").strip()
        if raw and raw[0].isdigit():
            level = int(raw[0])
            if 1 <= level <= 5:
                return level
    except Exception as e:
        logger.warning(f"Stress rater failed: {e}")
    return 1


# ── Telegram Handlers ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💚 Hi! I'm your Mental Health Companion.\n\n"
        "Feel free to share how you're feeling today.\n\n"
        "⚠️ I'm an AI — not a replacement for professional help.\n\n"
        "Commands:\n/start - Restart\n/clear - Clear history"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_sessions.pop(user_id, None)
    await update.message.reply_text("✅ Conversation cleared! Fresh start 💚")

def _trim_history(history: list) -> list:
    max_msgs = HISTORY_PAIRS_TO_KEEP * 2
    return history if len(history) <= max_msgs else history[-max_msgs:]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_int = update.effective_user.id
    user_id = str(user_id_int)
    user_text = update.message.text or ""

    if not OPENROUTER_API_KEY:
        await update.message.reply_text("❌ OPENROUTER_API_KEY missing from .env")
        return

    try:
        if user_id_int not in chat_sessions:
            chat_sessions[user_id_int] = []
            print(f"New session for user {user_id_int}")

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        if is_crisis(user_text):
            crisis_reply = (
                "💚 I hear you, and I'm really glad you reached out.\n\n"
                "What you're feeling right now is serious, and you deserve real support. "
                "Please reach out to a crisis helpline immediately:\n\n"
                "🇮🇳 *iCall (India):* 9152987821\n"
                "🌍 *Crisis Text Line:* Text HOME to 741741\n\n"
                "You are not alone. 💚"
            )
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🌸 Breathing Exercise", url=BREATHING_PAGE_URL)]])
            await update.message.reply_text(crisis_reply, parse_mode="Markdown", reply_markup=keyboard)
            return

        history = chat_sessions[user_id_int]
        history.append({"role": "user", "content": user_text})
        history = _trim_history(history)
        chat_sessions[user_id_int] = history

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        stress_level, reply = await asyncio.gather(
            get_stress_level(user_text, user_id=user_id),
            openrouter_chat(messages, user_id=user_id, max_tokens=220, temperature=0.7),
        )

        reply = (reply or "").strip() or "I'm here for you. Could you share more?"
        history.append({"role": "assistant", "content": reply})
        chat_sessions[user_id_int] = _trim_history(history)

        if stress_level >= 3:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🌸 Breathing Exercise", url=BREATHING_PAGE_URL)]])
            await update.message.reply_text(reply, reply_markup=keyboard)
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"❌ Error for user {user_id_int}: {e}")
        chat_sessions.pop(user_id_int, None)
        await update.message.reply_text("Sorry, something went wrong. Try /clear and send your message again.")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN missing from .env"); exit(1)
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY missing from .env"); exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot is running... Send /start on Telegram!")
    app.run_polling()
