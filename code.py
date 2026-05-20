# -*- coding: utf-8 -*-
import os
import time
import logging
import logging.handlers
import sys
from collections import defaultdict

from dotenv import load_dotenv
import telebot
from google import genai
from google.genai import errors as genai_errors

# ======================================================================
# 1️⃣  ENVIRONMENT LOADING & VALIDATION
# ======================================================================
load_dotenv(override=True)

TELEGRAM_BOT_TOKEN = os.getenv("8458132895:AAHzQ465lYyqyN0S2SpGq5d_hPUQJlkgMp4")
GEMINI_API_KEY = os.getenv("AIzaSyCOHbjzUEtfHqj6UQLdcFrcrNEFpYHAgJU")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    sys.stderr.write(
        "⚠️  .env ဖိုင်တွင် TELEGRAM_BOT_TOKEN နှင့် GEMINI_API_KEY လုံးဝဖြည့်ပေးပါ။\n"
    )
    sys.exit(1)

# ======================================================================
# 2️⃣  LOGGING CONFIGURATION (Rotating File + Console)
# ======================================================================
log_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log_handler = logging.handlers.RotatingFileHandler(
    "hackerai_bot.log",
    maxBytes=5 * 1024 ** 2,  # 5MB per file
    backupCount=3,           # Keep 3 backup files
    encoding="utf-8"
)
log_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger("HackerAI-Pro")
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(console_handler)

# ======================================================================
# 3️⃣  BOT & GEMINI CLIENT INITIALIZATION
# ======================================================================
bot = telebot.TeleBot(
    TELEGRAM_BOT_TOKEN,
    parse_mode="MarkdownV2",
    disable_web_page_preview=True,
    threaded=False,
)

genai.configure(api_key=GEMINI_API_KEY)
client = genai.GenerativeModel("gemini-2.5-pro")

SYSTEM_PROMPT = (
    "You are HackerAI Pro, an elite cybersecurity assistant and expert in technical security research. "
    "Your role is to assist authorized security professionals with code analysis, penetration testing methodologies, "
    "vulnerability remediation, and defensive engineering. Provide comprehensive, deeply technical, and structured replies "
    "suitable for educational and defensive auditing purposes. Always ensure code snippets are formatted perfectly. "
    "Reply in the same language the user uses. If the user writes in Burmese, reply in Burmese."
)

# ======================================================================
# 4️⃣  RATE-LIMITER (Per-Chat)
# ======================================================================
user_last_msg = defaultdict(lambda: 0.0)
COOLDOWN_SECONDS = 3.0


def is_on_cooldown(chat_id: int) -> bool:
    """
    Check if a user is on cooldown.
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        True if user is on cooldown, False otherwise
    """
    now = time.monotonic()
    if now - user_last_msg[chat_id] < COOLDOWN_SECONDS:
        return True
    user_last_msg[chat_id] = now
    return False


# ======================================================================
# 5️⃣  TEXT SPLITTING HELPER (Respects Telegram's 4096-byte limit)
# ======================================================================
def safe_split_text(text: str, limit: int = 4096):
    """
    Yield chunks of text that respect Telegram's character limit
    without breaking code blocks (triple backticks).
    
    Args:
        text: The text to split
        limit: Maximum characters per chunk (default: 4096)
        
    Yields:
        Chunks of text ≤ limit characters
    """
    if len(text) <= limit:
        yield text
        return

    # Split by code block markers to preserve them
    blocks = text.split("```")
    current\_chunk = ""

    for i, block in enumerate(blocks):
        # Even index = normal text, odd index = code block content
        if i % 2 == 0:
            # Normal text: split by lines
            for line in block.split("\n"):
                test\_line = line + "\n"
                if len(current\_chunk) + len(test\_line) <= limit:
                    current\_chunk += test\_line
                else:
                    if current\_chunk:
                        yield current\_chunk.rstrip("\n")
                    current\_chunk = test\_line
        else:
            # Code block: try to keep it together
            code\_block = f"```{block}```"
            if len(current\_chunk) + len(code\_block) <= limit:
                current\_chunk += code\_block
            else:
                if current\_chunk:
                    yield current\_chunk.rstrip("\n")
                current\_chunk = code\_block

    # Yield any remaining content
    if current\_chunk:
        yield current\_chunk.rstrip("\n")


# ======================================================================
# 6️⃣  MESSAGE HANDLERS
# ======================================================================
@bot.message\_handler(commands=["start"])
def send\_welcome(message: telebot.types.Message):
    """
    Handle /start command and send welcome message.
    
    Args:
        message: Telegram message object
    """
    welcome\_text = (
        "💀 \*HackerAI Pro \\$Gemini Version\$\* 💀\n\n"
        "ကျွန်တော့်ကတော့ Cybersecurity, Ethical Hacking နဲ့ Programming ပိုင်းဆိုင်ရာတွေကို "
        "စနစ်တကျ ကူညီပေးမယ့် AI ဖြစ်ပါတယ်။\n\n"
        "📌 မည်သည့်မေးခွန်းမဆို အောက်တွင် တိုက်ရိုက်ရိုက်ပြီး မေးမြန်းနိုင်ပါပြီ 👇\n\n"
        "\*Supported Commands:\*\n"
        "/start \\\- Show this welcome message\n"
        "Just type your question \\\- Get AI response"
    )
    try:
        bot.reply\_to(message, welcome\_text)
        logger.info("✅ Welcome message sent to %s", message.chat.id)
    except Exception as e:
        logger.error("❌ Error sending welcome message: %s", e)


@bot.message\_handler(commands=["help"])
def send\_help(message: telebot.types.Message):
    """
    Handle /help command.
    
    Args:
        message: Telegram message object
    """
    help\_text = (
        "🔧 \*HackerAI Pro Help\*\n\n"
        "\*Available Commands:\*\n"
        "/start \\\- Welcome message\n"
        "/help \\\- This help message\n\n"
        "\*How to use:\*\n"
        "1\\\. Send any cybersecurity or programming question\n"
        "2\\\. Wait for AI response \\$typing indicator\$\n"
        "3\\\. Get detailed, technical answers\n\n"
        "\*Rate Limiting:\*\n"
        "Maximum 1 message per 3 seconds per user\n\n"
        "\*Supported Topics:\*\n"
        "• Cybersecurity & penetration testing\n"
        "• Code analysis & vulnerability remediation\n"
        "• Defensive engineering\n"
        "• Programming in multiple languages"
    )
    try:
        bot.reply\_to(message, help\_text)
        logger.info("✅ Help message sent to %s", message.chat.id)
    except Exception as e:
        logger.error("❌ Error sending help message: %s", e)


@bot.message\_handler(func=lambda m: True)
def handle\_message(message: telebot.types.Message):
    """
    Main message handler for user queries.
    Processes input, calls Gemini API, and sends response.
    
    Args:
        message: Telegram message object
    """
    chat\_id = message.chat.id
    user\_id = message.from\_user.id
    username = message.from\_user.username or "Unknown"

    # Check rate limiting
    if is\_on\_cooldown(chat\_id):
        logger.warning("⏱️  Rate limit: User %s (%s) is on cooldown", user\_id, username)
        return

    # Show typing indicator
    bot.send\_chat\_action(chat\_id, "typing")

    # Get and validate user input
    user\_input = message.text.strip()
    if not user\_input:
        logger.warning("📝 Empty message from user %s (%s)", user\_id, username)
        return

    logger.info("📨 Message from %s (%s): %s", user\_id, username, user\_input[:100])

    try:
        # Call Gemini API with security-focused configuration
        response = client.generate\_content(
            user\_input,
            generation\_config=genai.types.GenerationConfig(
                temperature=0.3,           # Low temperature for deterministic responses
                max\_output\_tokens=4096,    # Maximum response length
                top\_p=0.95,                # Nucleus sampling
                stop\_sequences=None,
            ),
            system\_instruction=SYSTEM\_PROMPT,
        )

        # Extract and validate response
        reply = (
            response.text.strip()
            if response.text
            else "❌ အဖြေမရရှိပါ။ ပြန်လည်ကြိုးစားကြည့်ပါ။"
        )

        # Split and send response in chunks if necessary
        chunk\_count = 0
        for chunk in safe\_split\_text(reply):
            try:
                bot.reply\_to(message, chunk)
                chunk\_count += 1
            except telebot.apihelper.ApiException as e:
                logger.error("❌ Error sending chunk %d: %s", chunk\_count, e)
                break

        logger.info(
            "✅ Sent %d chunk(s) to user %s (%s)",
            chunk\_count,
            user\_id,
            username
        )

    except (genai\_errors.ClientError, genai\_errors.APIError) as e:
        error\_msg = f"❌ Gemini API error: {str(e)[:100]}"
        logger.error("🚫 Gemini API error for user %s (%s): %s", user\_id, username, e)
        try:
            bot.reply\_to(message, error\_msg)
        except telebot.apihelper.ApiException as te:
            logger.error("❌ Error sending error message: %s", te)

    except Exception as e:
        error\_msg = "❌ ခဏစောင့်ပါ။ System ပြန်လည်ချိတ်ဆက်နေပါသည်။"
        logger.exception("💥 Unexpected error for user %s (%s): %s", user\_id, username, e)
        try:
            bot.reply\_to(message, error\_msg)
        except telebot.apihelper.ApiException as te:
            logger.error("❌ Error sending error message: %s", te)


# ======================================================================
# 7️⃣  ENTRY POINT
# ======================================================================
def main():
    """Main function to start the bot."""
    logger.info("=" * 70)
    logger.info("🔹 Initializing HackerAI Pro Bot...")
    logger.info("🔹 Model: gemini-2.5-pro | SDK: google-genai")
    logger.info("🔹 Telegram Bot Token: \*\*\*" + TELEGRAM\_BOT\_TOKEN[-4:])
    logger.info("=" * 70)

    try:
        logger.info("🚀 Bot started. Polling for messages...")
        bot.infinity\_polling(interval=0.5, timeout=30, skip\_pending=True)

    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped manually by user.")
        sys.exit(0)

    except Exception as exc:
        logger.critical("💥 Fatal crash: %s", exc, exc\_info=True)
        sys.exit(1)


if __name__ == "\_\_main\_\_":
    main()
    