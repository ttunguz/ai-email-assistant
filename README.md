# AI Email Assistant for NeoMutt

An intelligent email assistant that generates contextual replies using AI models and semantic search through your email history.

## ✨ Features

- **🤖 AI-powered replies** using Ollama (Gemma 3 27B & Mistral 7B)
- **🔍 Semantic email search** with LanceDB for contextual awareness
- **⚡ High-performance daemon** that keeps models loaded for instant responses
- **🎯 Style matching** learns from your past emails to match your writing style
- **📧 NeoMutt integration** with simple F2 key binding
- **🚀 Auto-starting** daemon launches on first use
- **💬 Introduction email handling** with specialized templates

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    NeoMutt      │    │  auto_reply_     │    │  lancedb_       │
│   (F2 key)     │───▶│  single.py       │───▶│  daemon.py      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Ollama LLM     │    │   LanceDB +     │
                       │ (Gemma 3 27B)    │    │ SentenceXFormer │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **NeoMutt** email client
- **Ollama** with models: `gemma3:27b` and `mistral:7b-instruct`
- **notmuch** for email indexing
- **Python 3.8+**
- **uv** package manager

### Installation

1. **Clone this repository:**
   ```bash
   git clone <your-repo-url>
   cd <repo-name>
   ```

2. **Set up Python environment:**
   ```bash
   uv venv
   uv pip install -r requirements.txt
   ```

3. **Download Ollama models:**
   ```bash
   ollama pull gemma3:27b
   ollama pull mistral:7b-instruct
   ```

4. **Index your emails:**
   ```bash
   python3 build_lancedb_index.py
   ```

5. **Add to your `.muttrc`:**
   ```
   # AI Reply Generation
   macro index,pager <F2> "<pipe-message>~/.mutt/auto_reply_wrapper.sh<enter>" "Generate AI reply"
   ```

## 📖 Usage

### Basic Email Replies

1. Open an email in NeoMutt
2. Press **F2**
3. Wait for AI-generated reply (auto-starts daemon on first use)
4. Copy the reply text into your compose window

### With Custom Guidance

```bash
echo "Draft email content" | python3 auto_reply_single.py --guidance "Make this more casual"
```

### Introduction Emails

The system automatically detects introduction emails and uses specialized templates:

```bash
python3 auto_reply_single.py --intro  # Force intro mode
python3 auto_reply_single.py --auto-detect  # Auto-detect intros
```

## 🔧 Advanced Usage

### Daemon Management

```bash
# Check daemon status
./daemon_control.sh status

# Start daemon manually
./daemon_control.sh start

# Stop daemon
./daemon_control.sh stop

# View logs
./daemon_control.sh log
```

### Rebuilding Email Index

```bash
python3 build_lancedb_index.py
```

## 📁 Key Files

| File | Description |
|------|-------------|
| `auto_reply_single.py` | Main script for generating AI replies |
| `lancedb_daemon.py` | Background daemon for fast semantic search |
| `build_lancedb_index.py` | Builds searchable email index |
| `daemon_control.sh` | Daemon management script |
| `auto_reply_wrapper.sh` | Wrapper for NeoMutt integration |

## ⚙️ Configuration

### Email Indexing

Edit `build_lancedb_index.py` to customize:
- `notmuch_query`: Which emails to index
- `EMBEDDING_MODEL_NAME`: Embedding model for semantic search

### Writing Style

The AI learns from your email history automatically. To customize the style prompts, edit the prompts in `auto_reply_single.py`.

### Performance Tuning

- **Daemon auto-start**: Configured by default
- **Cache size**: Adjust `MAX_HISTORY_WORDS` in config
- **Search results**: Modify `limit` parameter in LanceDB queries

## 🔍 How It Works

1. **Email Indexing**: `build_lancedb_index.py` processes your notmuch database and creates vector embeddings of all emails using SentenceTransformers
2. **Semantic Search**: When you press F2, the current email is embedded and matched against your email history to find contextually similar conversations
3. **AI Generation**: Ollama generates a reply using the found context and learned writing style
4. **Performance**: The daemon keeps models loaded in memory for instant subsequent requests

## 🐛 Troubleshooting

### Daemon won't start
```bash
./daemon_control.sh log  # Check logs
./daemon_control.sh restart  # Force restart
```

### No email context found
```bash
python3 build_lancedb_index.py  # Rebuild index
notmuch new  # Update email database
```

### Models not found
```bash
ollama list  # Check installed models
ollama pull gemma3:27b  # Install missing models
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Add your preferred license]

## 🙏 Acknowledgments

- Built with [Ollama](https://ollama.ai/) for local LLM inference
- [LanceDB](https://lancedb.github.io/lancedb/) for vector similarity search
- [SentenceTransformers](https://www.sbert.net/) for email embeddings
- [NeoMutt](https://neomutt.org/) email client integration
