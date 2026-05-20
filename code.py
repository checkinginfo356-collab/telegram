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
client = genai.Client() # Initializing client with the correct modern google-genai SDK constructor

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
        Chunks of text <= limit characters
    """
    if len(text) <= limit:
        yield text
        return

    # Split by code block markers to preserve them
    blocks = text.split("```")
    current_chunk = ""

    for i, block in enumerate(blocks):
        # Even index = normal text, odd index = code block content
        if i % 2 == 0:
            # Normal text: split by lines
            for line in block.split("\n"):
                test_line = line + "\n"
                if len(current_chunk) + len(test_line) <= limit:
                    current_chunk += test_line
                else:
                    if current_chunk:
                        yield current_chunk.rstrip("\n")
                    current_chunk = test_line
        else:
            # Code block: try to keep it together
            code_block = f"```{block}```"
            if len(current_chunk) + len(code_block) <= limit:
                current_chunk += code_block
            else:
                if current_chunk:
                    yield current_chunk.rstrip("\n")
                current_chunk = code_block

    # Yield any remaining content
    if current_chunk:
        yield current_chunk.rstrip("\n")


# ======================================================================
# 6️⃣  MESSAGE HANDLERS
# ======================================================================
@bot.message_handler(commands=["start"])
def send_welcome(message: telebot.types.Message):
    """
    Handle /start command and send welcome message.
    
    Args:
        message: Telegram message object
    """
    welcome_text = (
        "💀 \*HackerAI Pro \\$Gemini Version\$\* 💀\n\n"
        "ကျွန်တော့်ကတော့ Cybersecurity, Ethical Hacking နဲ့ Programming ပိုင်းဆိုင်ရာတွေကို "
        "စနစ်တကျ ကူညီပေးမယ့် AI ဖြစ်ပါတယ်။\n\n"
        "📌 မည်သည့်မေးခွန်းမဆို အောက်တွင် တိုက်ရိုက်ရိုက်ပြီး မေးမြန်းနိုင်ပါပြီ 👇\n\n"
        "\*Supported Commands:\*\n"
        "/start \\\- Show this welcome message\n"
        "Just type your question \\\- Get AI response"
    )
    try:
        bot.reply_to(message, welcome_text)
        logger.info("✅ Welcome message sent to %s", message.chat.id)
    except Exception as e:
        logger.error("❌ Error sending welcome message: %s", e)


@bot.message_handler(commands=["help"])
def send_help(message: telebot.types.Message):
    """
    Handle /help command.
    
    Args:
        message: Telegram message object
    """
    help_text = (
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
        bot.reply_to(message, help_text)
        logger.info("✅ Help message sent to %s", message.chat.id)
    except Exception as e:
        logger.error("❌ Error sending help message: %s", e)


@bot.message_handler(func=lambda m: True)
def handle_message(message: telebot.types.Message):
    """
    Main message handler for user queries.
    Processes input, calls Gemini API, and sends response.
    
    Args:
        message: Telegram message object
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    # Check rate limiting
    if is_on_cooldown(chat_id):
        logger.warning("⏱️  Rate limit: User %s (%s) is on cooldown", user_id, username)
        return

    # Show typing indicator
    bot.send_chat_action(chat_id, "typing")

    # Get and validate user input
    user_input = message.text.strip()
    if not user_input:
        logger.warning("📝 Empty message from user %s (%s)", user_id, username)
        return

    logger.info("📨 Message from %s (%s): %s", user_id, username, user_input[:100])

    try:
        # Call Gemini API using google-genai SDK structures
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=user_input,
            config=genai.types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096,
                top_p=0.95,
                system_instruction=SYSTEM_PROMPT,
            )
        )

        # Extract and validate response
        reply = (
            response.text.strip()
            if response.text
            else "❌ အဖြေမရရှိပါ။ ပြန်လည်ကြိုးစားကြည့်ပါ။"
        )

        # Split and send response in chunks if necessary
        chunk_count = 0
        for chunk in safe_split_text(reply):
            try:
                bot.reply_to(message, chunk)
                chunk_count += 1
            except telebot.apihelper.ApiException as e:
                logger.error("❌ Error sending chunk %d: %s", chunk_count, e)
                break

        logger.info(
            "✅ Sent %d chunk(s) to user %s (%s)",
            chunk_count,
            user_id,
            username
        )

    except (genai_errors.ClientError, genai_errors.APIError) as e:
        error_msg = f"❌ Gemini API error: {str(e)[:100]}"
        logger.error("🚫 Gemini API error for user %s (%s): %s", user_id, username, e)
        try:
            bot.reply_to(message, error_msg)
        except telebot.apihelper.ApiException as te:
            logger.error("❌ Error sending error message: %s", te)

    except Exception as e:
        error_msg = "❌ ခဏစောင့်ပါ။ System ပြန်လည်ချိတ်ဆက်နေပါသည်။"
        logger.exception("💥 Unexpected error for user %s (%s): %s", user_id, username, e)
        try:
            bot.reply_to(message, error_msg)
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
    logger.info("🔹 Telegram Bot Token: ***" + TELEGRAM_BOT_TOKEN[-4:])
    logger.info("=" * 70)

    try:
        logger.info("🚀 Bot started. Polling for messages...")
        bot.infinity_polling(interval=0.5, timeout=30, skip_pending=True)

    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped manually by user.")
        sys.exit(0)

    except Exception as exc:
        logger.critical("💥 Fatal crash: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()