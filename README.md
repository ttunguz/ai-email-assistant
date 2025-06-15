# Complete NeoMutt + AI Email Setup Archive

A comprehensive email management system combining NeoMutt configuration, AI-powered reply generation, and productivity utilities. This is a complete personal email setup archive including configuration files, scripts, and an intelligent assistant system.

## ✨ Features

### 🤖 AI Email Assistant
- **AI-powered replies** using Ollama (Gemma 3 27B & Mistral 7B)
- **Semantic email search** with LanceDB for contextual awareness
- **High-performance daemon** that keeps models loaded for instant responses
- **Style matching** learns from your past emails to match your writing style
- **Introduction email handling** with specialized templates

### 📧 Complete NeoMutt Configuration
- **Multiple color themes** (Gruvbox, Zenburn, Solar, Base16, Orange, Capucin)
- **HTML email handling** with multiple viewer options
- **Notmuch integration** for powerful email search
- **URL extraction** and interactive selection
- **Offline email queuing** with msmtp
- **Gmail-style shortcuts** for navigation

### 🔧 Productivity Utilities
- **Interactive URL selection** from emails
- **HTML processing** and viewing scripts
- **Mail queue management** for offline scenarios
- **Email search** with notmuch integration
- **Automatic mail checking** and processing

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    NeoMutt      │    │  auto_reply_     │    │  lancedb_       │
│   (F2 key)     │───▶│  single.py       │───▶│  daemon.py      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                        │
        ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Notmuch Search │    │   Ollama LLM     │    │   LanceDB +     │
│  URL Selection  │    │ (Gemma 3 27B)    │    │ SentenceXFormer │
│  HTML Processing│    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │
        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│  msmtp Queue    │    │  Style Analysis  │
│  Mail Handling  │    │  Context Search  │
└─────────────────┘    └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **NeoMutt** email client
- **Ollama** with models: `gemma3:27b` and `mistral:7b-instruct`
- **notmuch** for email indexing
- **msmtp** for email sending
- **Python 3.8+** with **uv** package manager

### Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/ttunguz/ai-email-assistant.git
   cd ai-email-assistant
   ```

2. **Set up Python environment:**
   ```bash
   uv venv
   uv pip install -r requirements.txt
   ```

3. **Configure NeoMutt:**
   ```bash
   # Copy or symlink the main configuration
   cp .muttrc ~/.muttrc
   
   # Or use specific components
   source ~/.mutt/gruvbox.muttrc  # in your .muttrc for theme
   ```

4. **Download Ollama models:**
   ```bash
   ollama pull gemma3:27b
   ollama pull mistral:7b-instruct
   ```

5. **Index your emails:**
   ```bash
   python3 build_lancedb_index.py
   ```

## 📖 Usage

### AI Email Replies
- **F2** - Generate AI reply with context from email history
- **Ctrl+B** - Extract URLs from current message
- **O** - Interactive URL selection modal

### Email Navigation (Gmail-style)
- **Ctrl+E, N** - Notmuch search
- **Ctrl+E, T** - Reconstruct email thread
- **gi** - Go to inbox
- **gs** - Go to sent mail
- **ga** - View all mail
- **gd** - Go to drafts

### HTML Email Handling
- **H** or **V** - Open HTML in browser
- **B** - View HTML in Safari
- **T** - View as formatted text
- **L** - View with lynx
- **W** - View with w3m

## 📁 Configuration Files

### Core Configuration
| File | Description |
|------|-------------|
| `.muttrc` | Main NeoMutt configuration with all bindings |
| `mailcap` | File type associations for email attachments |
| `mailboxes` | Mailbox definitions and folders |

### Color Themes
| File | Description |
|------|-------------|
| `gruvbox.muttrc` | Gruvbox color theme |
| `zenburn.muttrc` | Zenburn color theme |
| `solar-dark.muttrc` | Solarized Dark theme |
| `base16.muttrc` | Base16 color scheme |
| `orange.muttrc` | Orange color theme |
| `capucin.muttrc` | Capucin color theme |

### AI Assistant Scripts
| File | Description |
|------|-------------|
| `auto_reply_single.py` | Main AI reply generation script |
| `lancedb_daemon.py` | Background daemon for semantic search |
| `build_lancedb_index.py` | Email indexing system |
| `daemon_control.sh` | Daemon management script |
| `auto_reply_wrapper.sh` | NeoMutt integration wrapper |

### Utility Scripts
| File | Description |
|------|-------------|
| `notmuch_py.py` | Python notmuch search interface |
| `notmuch.sh` | Shell notmuch integration |
| `select_url_modal.py` | Interactive URL selection |
| `extract_urls.sh` | Extract URLs from emails |
| `process_html.sh` | HTML email processing |
| `view_html.sh` | HTML viewing utilities |

### Mail Queue Management
| File | Description |
|------|-------------|
| `msmtp-enqueue.sh` | Queue emails for offline sending |
| `msmtp-runqueue.sh` | Process queued emails |
| `msmtpq-listqueue.sh` | List queued messages |
| `check_mail.sh` | Automated mail checking |

## ⚙️ Configuration

### Email Setup
- Configure your email accounts in separate config files
- Set up notmuch for email indexing
- Configure msmtp for email sending

### AI Assistant
- **Writing Style**: Automatically learns from your email history
- **Context Search**: Customize search parameters in `build_lancedb_index.py`
- **Models**: Switch between different Ollama models as needed

### Themes
Choose your preferred theme by sourcing it in your `.muttrc`:
```bash
source ~/.mutt/gruvbox.muttrc     # Dark theme
source ~/.mutt/solar-dark.muttrc  # Solarized
source ~/.mutt/zenburn.muttrc     # Easy on eyes
```

## 🔍 How It Works

1. **Email Management**: NeoMutt handles all email operations with custom key bindings
2. **Search Integration**: Notmuch provides fast, full-text email search
3. **AI Context**: LanceDB creates semantic embeddings of your email history
4. **Reply Generation**: Ollama generates contextually aware replies
5. **Offline Support**: msmtp queues emails when offline
6. **URL Handling**: Scripts extract and manage URLs from emails

## 🐛 Troubleshooting

### AI Assistant Issues
```bash
./daemon_control.sh status    # Check daemon
./daemon_control.sh restart   # Restart daemon
python3 build_lancedb_index.py  # Rebuild index
```

### Email Configuration
```bash
notmuch new              # Update email database
msmtp --serverinfo       # Test SMTP configuration
```

### Theme Issues
```bash
# Test colors in terminal
echo $TERM
# Ensure 256 color support
```

## 📄 Archive Notes

This is a complete personal email setup archive including:
- ✅ All configuration files and themes
- ✅ Custom scripts and utilities  
- ✅ AI assistant system
- ✅ Queue management tools
- ✅ Search and navigation helpers

## 🙏 Acknowledgments

- Built with [NeoMutt](https://neomutt.org/) email client
- [Ollama](https://ollama.ai/) for local LLM inference
- [LanceDB](https://lancedb.github.io/lancedb/) for vector similarity search
- [Notmuch](https://notmuchmail.org/) for email search
- [msmtp](https://marlam.de/msmtp/) for email sending
