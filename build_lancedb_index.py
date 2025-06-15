#!/usr/bin/env python3
"""
Builds a LanceDB vector index from a notmuch email database.

This script iterates through emails found by notmuch, generates embeddings
for the email bodies using an Ollama model, and stores them in a LanceDB table
for fast semantic search.
"""

import os
import sys
import subprocess
import email
import email.header
import re
import json
import lancedb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from pydantic import BaseModel
import lancedb.pydantic as ldb

# --- Configuration ---
DB_PATH = os.path.expanduser("~/.mutt/lancedb")
TABLE_NAME = "emails"
# Using a local SentenceTransformer model is faster and more reliable for bulk processing.
# This model is small, fast, and effective for semantic search.
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2' 
BATCH_SIZE = 100  # Process emails in batches

# --- Helper Functions ---

def decode_header(header):
    """Safely decode email headers."""
    if not header:
        return ""
    try:
        decoded_parts = []
        for part, encoding in email.header.decode_header(header):
            if isinstance(part, bytes):
                # If no encoding is specified, default to utf-8
                charset = encoding or 'utf-8'
                try:
                    decoded_parts.append(part.decode(charset, errors='replace'))
                except (UnicodeDecodeError, LookupError):
                    # Fallback to a common encoding if the specified one fails
                    decoded_parts.append(part.decode('latin-1', errors='replace'))
            else:
                decoded_parts.append(str(part))
        return ' '.join(decoded_parts)
    except Exception:
        return str(header) # Return raw header as a fallback

def extract_name_email(from_header):
    """Extract name and email from a From: header string."""
    if not from_header:
        return "", ""
    name, addr = email.utils.parseaddr(decode_header(from_header))
    return name, addr

def get_email_body(msg):
    """Extracts the plain text body from an email.message object."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get("Content-Disposition")
            # Ensure it's text/plain and not an attachment
            if content_type == 'text/plain' and (disposition is None or "attachment" not in disposition.lower()):
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    break  # Found the plain text body
                except:
                    continue # Try the next part
    else:
        # Not multipart, just get the payload if it's text/plain
        if msg.get_content_type() == 'text/plain':
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='replace')
            except:
                body = ""  # Could not decode
    
    # Simple cleanup of the body
    # Remove quoted reply headers like "On Date, Person wrote:"
    body = re.sub(r'On.*wrote:\n', '', body, flags=re.IGNORECASE)
    # Remove lines that are just quotes of a previous email
    lines = [line for line in body.split('\n') if not line.strip().startswith('>')]
    # Re-join and strip signature if present
    cleaned_body = "\n".join(lines)
    cleaned_body = cleaned_body.split('-- \n')[0].strip()
    return cleaned_body

def main():
    print("Starting to build LanceDB email index...")
    
    # 1. Load the embedding model
    print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        embedding_dim = model.get_sentence_embedding_dimension()
        print(f"Model loaded. Embedding dimension: {embedding_dim}")
    except Exception as e:
        print(f"Error loading SentenceTransformer model: {e}", file=sys.stderr)
        print("Please ensure you have an internet connection for the first run to download the model.", file=sys.stderr)
        sys.exit(1)

    # 2. Define the Pydantic model for our LanceDB table schema
    class EmailModel(ldb.LanceModel):
        vector: ldb.Vector(embedding_dim)
        text: str
        subject: str
        sender: str
        path: str
        date: str

    # 3. Connect to LanceDB and create/open the table
    db = lancedb.connect(DB_PATH)
    try:
        # Overwrite to ensure a fresh index each time
        tbl = db.create_table(TABLE_NAME, schema=EmailModel, mode="overwrite")
        print(f"Created new table '{TABLE_NAME}' in '{DB_PATH}'")
    except Exception as e:
        print(f"Error creating LanceDB table: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Get email file paths from notmuch
    print("Querying notmuch for email file paths...")
    try:
        # Broad query to get all relevant emails, excluding drafts and trash
        notmuch_query = "*" # Search for ALL emails
        cmd = ["notmuch", "search", "--output=files", notmuch_query]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        file_paths = result.stdout.strip().split('\n')
        print(f"Found {len(file_paths)} emails to process.")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Failed to query notmuch: {e}", file=sys.stderr)
        print("Please ensure 'notmuch' is installed and configured.", file=sys.stderr)
        sys.exit(1)
        
    # 5. Process emails and add to LanceDB
    data_to_add = []
    for path in tqdm(file_paths, desc="Embedding emails", unit="email"):
        if not path or not os.path.exists(path):
            continue
            
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                msg = email.message_from_file(f)
            
            body = get_email_body(msg)
            if not body:
                continue
            
            # Create a dictionary matching the Pydantic model
            sender_name, sender_email = extract_name_email(msg.get('From'))
            data = {
                "text": body,
                "subject": decode_header(msg.get('Subject', '')),
                "sender": f"{sender_name} <{sender_email}>".strip(),
                "path": path,
                "date": msg.get('Date', '')
            }
            data_to_add.append(data)
            
        except Exception as e:
            tqdm.write(f"Skipping file {path} due to error: {e}", file=sys.stderr)

    # 6. Generate embeddings and add data if any exists
    if data_to_add:
        print(f"\nGenerating embeddings for {len(data_to_add)} emails...")
        texts_to_embed = [d['text'] for d in data_to_add]
        embeddings = model.encode(texts_to_embed, show_progress_bar=True)
        
        # Add the generated vectors back to our data
        for i, data in enumerate(data_to_add):
            data['vector'] = embeddings[i]

        # 7. Add the complete data to the LanceDB table
        print("Adding data to LanceDB table...")
        tbl.add(data_to_add)
        print("Data added. Current table contents:")
        # print(tbl.to_pandas())

    print(f"\nTotal rows in table: {len(tbl)}")
    
    # 8. Create a search index for performance, only if table is not empty
    if len(tbl) > 0:
        print("Creating search index on vector column for faster queries...")
        try:
            tbl.create_index()
            print("Search index created successfully.")
        except Exception as e:
            print(f"Could not create search index. Queries may be slow. Error: {e}", file=sys.stderr)
    else:
        print("Skipping index creation as the table is empty.")

    print("\nIndexing complete!")

if __name__ == "__main__":
    main() 