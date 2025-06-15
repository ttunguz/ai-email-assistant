#!/Users/tomasztunguz/.mutt/.venv/bin/python3
"""
LanceDB Background Daemon for Email Context Search

This daemon loads the SentenceTransformer model and LanceDB once, then serves
semantic search requests via a Unix socket for fast response times.
"""

import os
import sys
import socket
import json
import signal
import logging
from pathlib import Path

# Suppress HuggingFace tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    import lancedb
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: Required packages not found. Make sure you're using the virtual environment.", file=sys.stderr)
    sys.exit(1)

# Configuration
DB_PATH = os.path.expanduser("~/.mutt/lancedb")
TABLE_NAME = "emails" 
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
SOCKET_PATH = "/tmp/lancedb_daemon.sock"
PID_FILE = os.path.expanduser("~/.mutt/lancedb_daemon.pid")

# Global components
model = None
db = None
table = None

def setup_logging():
    """Set up logging to file."""
    log_file = os.path.expanduser("~/.mutt/lancedb_daemon.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def load_components():
    """Load LanceDB components once at startup."""
    global model, db, table
    
    logging.info("Loading SentenceTransformer model...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    logging.info("Connecting to LanceDB...")
    db = lancedb.connect(DB_PATH)
    table = db.open_table(TABLE_NAME)
    
    logging.info("Components loaded successfully!")

def search_similar_emails(query_text, limit=3):
    """Search for similar emails using the loaded components."""
    if not query_text or not all([model, db, table]):
        return []
    
    try:
        query_vector = model.encode(query_text)
        results = table.search(query_vector).limit(limit).to_pandas()
        
        if results.empty:
            return []
        
        emails = []
        for _, row in results.iterrows():
            emails.append({
                'date': row['date'],
                'sender': row['sender'], 
                'subject': row['subject'],
                'text': row['text']
            })
        
        return emails
        
    except Exception as e:
        logging.error(f"Error during search: {e}")
        return []

def handle_request(data):
    """Handle a search request."""
    try:
        request = json.loads(data)
        query_text = request.get('query', '')
        limit = request.get('limit', 3)
        
        emails = search_similar_emails(query_text, limit)
        
        response = {
            'status': 'success',
            'emails': emails
        }
        
    except Exception as e:
        logging.error(f"Error handling request: {e}")
        response = {
            'status': 'error', 
            'message': str(e)
        }
    
    return json.dumps(response)

def cleanup():
    """Clean up socket and PID file."""
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    if os.path.exists(PID_FILE):
        os.unlink(PID_FILE)

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logging.info("Received shutdown signal, cleaning up...")
    cleanup()
    sys.exit(0)

def main():
    setup_logging()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    # Clean up any existing socket
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    
    logging.info("Starting LanceDB daemon...")
    
    # Load components
    try:
        load_components()
    except Exception as e:
        logging.error(f"Failed to load components: {e}")
        sys.exit(1)
    
    # Create socket server
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(SOCKET_PATH)
    sock.listen(1)
    
    logging.info(f"Daemon listening on {SOCKET_PATH}")
    
    try:
        while True:
            conn, addr = sock.accept()
            try:
                data = conn.recv(4096).decode('utf-8')
                if data:
                    response = handle_request(data)
                    conn.send(response.encode('utf-8'))
            except Exception as e:
                logging.error(f"Error handling connection: {e}")
            finally:
                conn.close()
                
    except KeyboardInterrupt:
        logging.info("Daemon interrupted by user")
    finally:
        sock.close()
        cleanup()

if __name__ == "__main__":
    main() 