# 🧠 AI Mental Health Companion - Telegram Bot

A compassionate, AI-powered Telegram chatbot designed to provide empathetic emotional support, evaluate stress levels, and offer guided breathing exercises. This project was developed as an internship project to provide immediate conversational support while prioritizing user safety through built-in crisis detection and fallback model routing.

## ✨ Key Features

- **Compassionate AI Chat:** Provides warm, empathetic responses using a custom-tuned system prompt.
- **Dynamic Model Routing & Failover:** Automatically fetches available free LLMs from OpenRouter and cycles through them. If a model fails or hits a rate limit, the bot instantly falls back to the next available model without interrupting the user.
- **Real-time Stress Triage:** Runs a secondary AI check in the background to rate the user's emotional distress from 1-5. If stress is rated 3 or higher, it suggests a guided breathing exercise.
- **Hardcoded Crisis Detection:** Scans user input for critical keywords. If severe distress is detected, the AI is bypassed immediately, and the user is provided with real-world crisis helplines.
- **Asynchronous Processing:** Built with `python-telegram-bot` and `asyncio` to handle multiple users simultaneously without blocking.

## 📋 Prerequisites

Before you begin, ensure you have the following:
- [Python 3.8+](https://www.python.org/downloads/) installed on your machine.
- A Telegram account.
- An [OpenRouter](https://openrouter.ai/) account for API access.

## 🚀 Installation & Setup

You can download the project using either Git (Method 1) or directly from your browser without Git (Method 2).

### Method 1: Using Git (Recommended)
Open your terminal or command prompt and run the following commands:
```bash
git clone https://github.com/xsharmas/Brainhealer_bot.git
cd Brainhealer_bot
```

### Method 2: Without Git (Download ZIP)
1. Go to the project repository page: [https://github.com/xsharmas/Brainhealer_bot](https://github.com/xsharmas/Brainhealer_bot)
2. Click on the green **<> Code** button.
3. Select **Download ZIP**.
4. Extract the downloaded ZIP file to your preferred location.
5. Open your terminal or command prompt and navigate (`cd`) into the extracted folder.
### Method 3: Copy each file and create folder in your IDE.(Then install requirements.txt and run app.py)
```
*(If you downloaded the ZIP file directly from GitHub, extract it and open your terminal in that folder).*

### 2. Install Dependencies
Install the required Python packages using the provided `requirements.txt` file:
```bash
pip install -r requirements.txt
```
### Method 3: Copy each file and create folder in your IDE.(Then install requirements.txt and run app.py)

  
### 3. Configure Environment Variables (API Keys)
You need to provide your own API keys to run this bot. **Never share your `.env` file or commit it to GitHub.**

Create a new file in the root directory named `.env` and paste the following template:

```ini
# --- TELEGRAM BOT TOKEN ---
# Get this from @BotFather on Telegram
TELEGRAM_TOKEN=your_telegram_bot_token_here

# --- OPENROUTER API KEY ---
# Get this from https://openrouter.ai/keys
OPENROUTER_API_KEY=your_openrouter_api_key_here

# --- URL CONFIGURATION ---
BREATHING_PAGE_URL=https://yourusername.github.io/Breathe/

# --- MODEL SETTINGS ---
MODEL_FAILURE_THRESHOLD=2
MODEL_COOLDOWN_SECONDS=60
```
Replace `your_telegram_bot_token_here` and `your_openrouter_api_key_here` with your actual keys.

## 💻 Running the Bot

Once your dependencies are installed and your `.env` file is securely set up, start the bot:

```bash
python app.py
```

If successful, you will see output similar to this in your terminal:
```text
🤖 Bot starting... TELEGRAM_TOKEN: ✅
🧠 OpenRouter key: ✅
🔄 Fetching live free models from OpenRouter...
✅ Found 24 free models.
🧩 Loaded 24 models to cycle through.
🚀 Bot is running... Send /start on Telegram!
```

## 📱 Usage

1. Open Telegram and search for your bot's username.
2. Send the `/start` command to initiate the conversation.
3. Chat naturally. If you want to wipe the bot's memory of your current conversation and start fresh, use the `/clear` command.

## ⚠️ Disclaimer

**This bot is an AI, not a licensed medical professional.** It is designed for conversational support and companionship only. It cannot diagnose or treat mental health conditions. If you or someone you know is in crisis, please reach out to local emergency services or a professional crisis helpline immediately.
