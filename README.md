# 🤖 AI Intelligence Digest

An automated, config-driven intelligence digest system that curates and delivers personalized content from multiple sources using LLMs.

## ✨ Features

- **Modular Pipeline Architecture** - Add new digest pipelines entirely via YAML config
- **Multiple Sources** - Reddit, Hacker News, RSS feeds, Product Hunt
- **LLM-Powered Curation** - Uses Ollama for intelligent content evaluation
- **Smart Deduplication** - SQL + FAISS-based semantic deduplication
- **Multiple Delivery Channels** - Email, Telegram, File output
- **Beautiful Email Templates** - Customizable colors and formatting

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/download) with `llama3.1:8b` model

### Setup

**Windows:**
```batch
setup.bat
```

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Copy environment file:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` with your credentials:
   ```env
   EMAIL_USERNAME=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

5. Start Ollama:
   ```bash
   ollama serve
   ollama pull llama3.1:8b
   ```

6. Run the digest:
   ```bash
   cd src
   python -m cli.run
   ```

## ⚙️ Configuration

All configuration is in `resources/config.yml`.

### Pipeline Configuration

Pipelines are fully modular. Each pipeline defines:

```yaml
pipelines:
  my_pipeline:
    enabled: true
    persona: GENAI_NEWS  # Must match a persona in core/personas.py
    fetch_hours: 24
    default_audience: developer
    score_field: relevance_score
    why_it_matters_field: why_it_matters
    why_it_matters_fallback: "Relevant update."
    ingestion:
      top_k: 5
      sources:
        - type: reddit
          enabled: true
          subreddit: MachineLearning
        - type: rss
          enabled: true
          name: my_feeds
          feeds:
            - https://example.com/feed.xml
        - type: hackernews
          enabled: true
        - type: producthunt
          enabled: false
      keywords:
        - keyword1
        - keyword2
      min_engagement: 5
```

### Email Customization

Customize email template colors:

```yaml
email_colors:
  primary: "#00F6FF"
  primary_dark: "#0047FF"
  secondary: "#B896FF"
  background: "#060606"
  card_bg: "#060606"
  text_primary: "#FBFAFA"
  text_secondary: "#7BA8FF"
  border: "#0047FF"
  accent: "#00FFF0"
  why_it_matters_bg: "#060606"
  why_it_matters_text: "#00FFF0"
```

### Delivery Channels

```yaml
# Email
EMAIL_ENABLED: "true"
EMAIL_SMTP_HOST: smtp.gmail.com
EMAIL_SMTP_PORT: 587
EMAIL_FROM: your_email@gmail.com
EMAIL_TO: recipient@gmail.com

# Telegram
TELEGRAM_ENABLED: "false"
```

## 📁 Project Structure

```
AI-Digest/
├── resources/
│   └── config.yml          # Main configuration
├── src/
│   ├── cli/
│   │   └── run.py          # Main entry point
│   ├── core/
│   │   ├── entities.py     # Data models
│   │   ├── personas.py     # Persona definitions
│   │   └── schemas.py      # Evaluation schemas
│   ├── delivery/
│   │   ├── email_delivery.py
│   │   ├── file_delivery.py
│   │   └── telegram_delivery.py
│   ├── ingestion/
│   │   ├── reddit.py
│   │   ├── hackernews.py
│   │   ├── rss.py
│   │   └── producthunt.py
│   ├── processing/
│   │   ├── evaluator.py    # LLM evaluation
│   │   ├── deduplicator.py
│   │   └── prefilter.py
│   ├── services/
│   │   ├── config.py       # Config loading
│   │   ├── llm.py          # Ollama client
│   │   └── database.py     # SQLite storage
│   └── workflows/
│       ├── pipeline_factory.py  # Dynamic pipeline creation
│       ├── genai_news.py
│       └── product_ideas.py
├── data/                   # Database & FAISS index
├── output/                 # Generated digest files
├── .env                    # Secrets (not in git)
├── .env.example            # Template for .env
├── setup.bat               # Windows setup script
├── setup.sh                # Linux/macOS setup script
└── pyproject.toml          # Python dependencies
```

## 🔧 Adding a New Pipeline

1. **Define a new persona** in `src/core/personas.py`:
   ```python
   MY_PERSONA = Persona(
       name="MY_PERSONA",
       description="Description of what this persona curates",
       evaluation_schema=MyEvaluationSchema,
       min_score=0.5,
   )
   
   ALL_PERSONAS["MY_PERSONA"] = MY_PERSONA
   ```

2. **Create evaluation schema** in `src/core/schemas.py`:
   ```python
   class MyEvaluationSchema(BaseModel):
       relevance_score: float = Field(..., ge=0.0, le=1.0)
       # ... other fields
   ```

3. **Add pipeline config** in `resources/config.yml`:
   ```yaml
   pipelines:
     my_new_pipeline:
       enabled: true
       persona: MY_PERSONA
       # ... rest of config
   ```

4. Run the digest - your new pipeline will be automatically created!

## 🌐 Web GUI

AI-Digest includes a web-based frontend for managing users, subscriptions, and configurations.

### Quick Start

```bash
cd src

# Initialize database
python -m gui.run_gui init-db

# Create admin user
python -m gui.run_gui create-admin

# Start web server
python -m gui.run_gui run --port 5000
```

Open http://localhost:5000 in your browser.

### Features

- **User Registration** - Email-based signup with OTP verification
- **Persona Subscriptions** - Users select which digests to receive
- **Admin Dashboard** - Manage users, pipelines, and config
- **Multi-user Delivery** - Digests sent to all subscribed users
- **Config Editor** - Edit settings and colors from the web

See [src/gui/README.md](src/gui/README.md) for full documentation.

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
