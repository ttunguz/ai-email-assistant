#!/Users/tomasztunguz/.mutt/.venv/bin/python3
"""
Single Email Auto Reply Script for Mutt using Ollama (Gemma 3 27B & Mistral 7B)

This script:
1. Reads an email from stdin
2. Uses Gemma 3 27B to generate an appropriate reply
3. Uses Mistral 7B Instruct for list detection and reformatting
4. Outputs the reply to stdout

Usage: python3 auto_reply_single.py [--guidance "your guidance here"] [--intro]
"""

import os
import sys

# Suppress HuggingFace tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# No longer need to load heavy dependencies directly - daemon handles this
import email
import email.utils
import email.header
import subprocess
import re
import argparse
import socket
import json
import time

# Configuration
YOUR_EMAIL = "tt@theory.ventures"
YOUR_NAME = "Tomasz Tunguz"
MODEL = "mistral:7b-instruct"  # For list detection and reformatting
GENERATION_MODEL = "mistral:7b-instruct"  # For email text generation
# Approximate token limit (128k tokens ~= 96k words. Use 80k words as a buffer)
MAX_HISTORY_WORDS = 80000

# --- Daemon Configuration ---
SOCKET_PATH = "/tmp/lancedb_daemon.sock"

def decode_header(header):
    """Decode email header correctly."""
    decoded_header = email.header.decode_header(header)
    header_parts = []
    for part, encoding in decoded_header:
        if isinstance(part, bytes):
            if encoding:
                try:
                    part = part.decode(encoding)
                except UnicodeDecodeError:
                    part = part.decode('utf-8', errors='replace')
            else:
                part = part.decode('utf-8', errors='replace')
        header_parts.append(str(part))
    return ' '.join(header_parts)

def extract_name_email(from_header):
    """Extract name and email from From header."""
    from_header = decode_header(from_header)
    try:
        name, email_addr = email.utils.parseaddr(from_header)
        # Simple fix for common case where name might be empty but email is in name part
        if not email_addr and '@' in name:
            # Attempt to extract email from name part if parseaddr fails to separate
            match = re.search(r'<([^>]+)>', name)
            if match:
                email_addr = match.group(1)
                name_part = name.replace(f"<{email_addr}>", "").strip()
                if name_part: # Take the part before <email> as name
                    name = name_part 
                # If name was just "<email>", try to get it from local part
                elif email_addr and not name_part: 
                    name = email_addr.split('@')[0] 
            elif '@' in name and ' ' not in name : # If name is just an email address
                 email_addr = name
                 name = email_addr.split('@')[0]

        return name, email_addr
    except:
        return from_header, ""

def get_email_body_from_file(file_path):
    """Parses a single email file and returns its plain text body and sender info."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            msg = email.message_from_file(f)
        
        # Extract sender information
        from_header = msg.get('From', '')
        sender_name, sender_email = extract_name_email(from_header)
        
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = part.get("Content-Disposition")
                if content_type == 'text/plain' and (disposition is None or "attachment" not in disposition.lower()):
                    try:
                        charset = part.get_content_charset() or 'utf-8'
                        payload = part.get_payload(decode=True)
                        text = payload.decode(charset, errors='replace')
                        body = text
                        break 
                    except UnicodeDecodeError:
                        # Fallback decoding
                        body = payload.decode('utf-8', errors='replace')
                        break
                    except Exception:
                        # Skip parts that can't be decoded or processed
                        continue
        else:
            # Not multipart, try to get body if plain text
            content_type = msg.get_content_type()
            if content_type == 'text/plain':
                try:
                    charset = msg.get_content_charset() or 'utf-8'
                    payload = msg.get_payload(decode=True)
                    body = payload.decode(charset, errors='replace')
                except Exception:
                    # Fallback decoding for non-multipart
                    body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
        
        return {
            'body': body.strip(),
            'sender_email': sender_email,
            'sender_name': sender_name
        }
    except Exception as e:
        # print(f"Error reading or parsing email file {file_path}: {e}", file=sys.stderr)
        return {
            'body': '',
            'sender_email': '',
            'sender_name': ''
        }

def start_daemon_if_needed():
    """Start the daemon if it's not already running."""
    daemon_script = os.path.expanduser("~/.mutt/lancedb_daemon.py")
    pid_file = os.path.expanduser("~/.mutt/lancedb_daemon.pid")
    socket_path = "/tmp/lancedb_daemon.sock"
    
    # Check if daemon is already running
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            # Check if process is actually running
            os.kill(pid, 0)  # This will raise an exception if process doesn't exist
            return True  # Daemon is running
        except (OSError, ValueError):
            # PID file exists but process is dead, clean up
            if os.path.exists(pid_file):
                os.unlink(pid_file)
            if os.path.exists(socket_path):
                os.unlink(socket_path)
    
    # Start the daemon
    print("Starting email context daemon... (this may take 30-60 seconds on first run)", file=sys.stderr)
    
    try:
        # Start daemon in background
        daemon_dir = os.path.dirname(daemon_script)
        process = subprocess.Popen([daemon_script], 
                                 cwd=daemon_dir,
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
        
        # Wait for daemon to be ready (check for socket file)
        max_wait = 60  # seconds
        for i in range(max_wait):
            if os.path.exists(socket_path):
                # Give it one more second to fully initialize
                time.sleep(1)
                print("Daemon ready!", file=sys.stderr)
                return True
            time.sleep(1)
        
        print("Warning: Daemon took too long to start", file=sys.stderr)
        return False
        
    except Exception as e:
        print(f"Error starting daemon: {e}", file=sys.stderr)
        return False

def get_similar_emails_from_lancedb(query_text: str, limit: int = 3):
    """
    Searches for semantically similar emails using the background daemon.
    Automatically starts the daemon if it's not running.
    """
    if not query_text:
        return ""

    # Auto-start daemon if needed
    if not start_daemon_if_needed():
        print("Could not start daemon, proceeding without context", file=sys.stderr)
        return ""

    try:
        # Connect to daemon
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        sock.connect(SOCKET_PATH)
        
        # Send request
        request = json.dumps({"query": query_text, "limit": limit})
        sock.sendall(request.encode('utf-8'))
        
        # Receive response
        response_data = sock.recv(8192).decode('utf-8')
        sock.close()
        
        response = json.loads(response_data)
        
        if response.get('status') != 'success':
            print(f"Daemon error: {response.get('message', 'Unknown error')}", file=sys.stderr)
            return ""
        
        emails = response.get('emails', [])
        
        if not emails:
            return ""
        
        history_texts = []
        for email in emails:
            context = f"On {email['date']}, {email['sender']} wrote:\nSubject: {email['subject']}\nBody:\n{email['text']}"
            history_texts.append(context)

        return "\n\n---\n\n".join(history_texts)
        
    except socket.timeout:
        print("Daemon request timed out", file=sys.stderr)
        return ""
    except FileNotFoundError:
        print("Daemon socket not found", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Error communicating with daemon: {e}", file=sys.stderr)
        return ""

def get_previous_emails_content(sender_email, max_words=MAX_HISTORY_WORDS):
    """
    DEPRECATED: This function previously used notmuch to get email history.
    It is now replaced by get_similar_emails_from_lancedb for semantic context.
    This function is kept to avoid breaking existing call sites until fully refactored.
    """
    return "" # Return empty string to effectively disable it.

def is_introduction_email(subject, body, to_header, cc_header):
    """Determine if this is an introduction email."""
    # Add debugging output
    # print(f"DEBUG: Checking if email is an introduction...", file=sys.stderr)
    # print(f"DEBUG: Subject: {subject}", file=sys.stderr)
    # print(f"DEBUG: To header: {to_header}", file=sys.stderr)
    # print(f"DEBUG: CC header: {cc_header}", file=sys.stderr)
    
    # Check if there are multiple recipients (more than one To: or at least one CC:)
    to_addresses = []
    cc_addresses = []
    
    if to_header:
        # Split by commas outside of quotes
        to_parts = re.findall(r'(?:[^,"]|"(?:\\.|[^"])*")+', to_header)
        to_addresses = [part.strip() for part in to_parts if part.strip()]
    
    if cc_header:
        cc_parts = re.findall(r'(?:[^,"]|"(?:\\.|[^"])*")+', cc_header)
        cc_addresses = [part.strip() for part in cc_parts if part.strip()]
    
    # Print the recipients we found for debugging
    # print(f"DEBUG: To addresses: {to_addresses}", file=sys.stderr)
    # print(f"DEBUG: CC addresses: {cc_addresses}", file=sys.stderr)
    
    has_multiple_recipients = len(to_addresses) > 1 or len(cc_addresses) > 0
    
    # Look for introduction patterns in the subject
    subject_patterns = [
        r'(?i)intro(?:duction)?(?:\s+(?:to|for|with))?',
        r'(?i)meet(?:ing)?',
        r'(?i)connect(?:ing)?(?:\s+(?:you|with))?',
        r'(?i)(?:would|want|like|love|pleased)(?:\s+to)?(?:\s+introduce)',
    ]
    
    # Look for introduction patterns in the body
    body_patterns = [
        r'(?i)(?:would|want|like|love|pleased)(?:\s+to)?(?:\s+introduce)',
        r'(?i)I(?:\s+am|\s+would)?(?:\s+like)?(?:\s+to)?(?:\s+introduce)',
        r'(?i)(?:I|I)(?:\'|\')?(?:t\'?s)?(?:\s+(?:my|a))?(?:\s+pleasure)(?:\s+to)?(?:\s+introduce)',
        r'(?i)(?:I|I)(?:\'|\')?m(?:\s+(?:happy|glad|excited|pleased))(?:\s+to)?(?:\s+introduce)',
        r'(?i)(?:allow|let)(?:\s+me)?(?:\s+to)?(?:\s+introduce)',
        r'(?i)meet(?:ing)?(?:\s+each(?:\s+other)?)?',
        r'(?i)(?:hoping|hope|thought)(?:\s+(?:you|to|that))?(?:\s+(?:two|both))?(?:\s+(?:could|would|might|can))?(?:\s+connect)',
        r'(?i)(?:cc|copying)(?:ing)?(?:\s+you(?:\s+both)?)?(?:\s+(?:to|so|for))?',
        r'(?i)(?:bringing|looping|adding)(?:\s+(?:you|in))?(?:\s+(?:both|two|together))?',
        r'(?i)take(?:\s+it)?(?:\s+from)?(?:\s+here)',
        r'(?i)enjoy(?:\s+connecting)',
        r'(?i)glad(?:\s+to)?(?:\s+make)?(?:\s+the)?(?:\s+introduction)',
        r'(?i)founder(?:\s+of)',
    ]
    
    # Check if subject contains introduction patterns
    subject_match = any(re.search(pattern, subject) for pattern in subject_patterns)
    
    # Check if body contains introduction patterns
    matching_patterns = []
    for pattern in body_patterns:
        match = re.search(pattern, body)
        if match:
            matching_patterns.append((pattern, match.group(0)))
    
    body_match = len(matching_patterns) > 0
    
    # Additional heuristics for introductions
    name_followed_by_is = re.search(r'(?i)[A-Z][a-z]+,\s+[A-Z][a-z]+\s+is', body)
    two_name_occurrences = re.findall(r'(?i)[A-Z][a-z]+\s+[A-Z][a-z]+', body)
    has_multiple_names = len(set(two_name_occurrences)) >= 2 if two_name_occurrences else False
    
    # Three ways to determine it's an introduction:
    # 1. Subject looks like an intro AND has multiple recipients
    # 2. Body contains intro patterns AND has multiple recipients
    # 3. Has the "Name, Other is..." pattern (common in introductions)
    is_intro = (subject_match and has_multiple_recipients) or \
               (body_match and has_multiple_recipients) or \
               bool(name_followed_by_is) or \
               (has_multiple_names and ("let" in body.lower() or "take it from here" in body.lower()))
    
    return is_intro

def get_other_person_info(email_obj):
    """Extract the other person's name and email from an introduction email."""
    # Helper function to extract recipients from header
    def extract_recipients(header_content):
        if not header_content:
            return []
        # Split the header by commas not enclosed in quotes
        parts = re.findall(r'(?:[^,"]|"(?:\\\\.|[^"])*")+', header_content)
        return [extract_name_email(part.strip()) for part in parts if part.strip()]
    
    # Get all recipients from To and CC
    to_recipients = extract_recipients(email_obj.get('to', ''))
    cc_recipients = extract_recipients(email_obj.get('cc', ''))
    all_recipients = to_recipients + cc_recipients
    
    # Filter out yourself
    other_people = [(name, email_addr) for name, email_addr in all_recipients 
                   if email_addr and email_addr.lower() != YOUR_EMAIL.lower()]
    
    current_sender_email = email_obj.get('sender_email', '')
    # First check headers for the introducee
    if other_people:
        # Just take the first person that's not the sender
        for name, email_addr in other_people:
            if email_addr and email_addr.lower() != current_sender_email.lower():
                return name, email_addr
    
    # If not found in headers, try to extract from the email body
    body = email_obj.get('body', '')
    
    # Try common introduction patterns in the body
    intro_patterns = [
        # "I'd like to introduce you to [Name]"
        r'(?i)(?:introduce|introducing|introduction|connect|connecting)(?:\s+(?:you|to))(?:\s+(?:to|with))?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
        # "[Name], founder of..."
        r'(?i)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\s*,)(?:\s+(?:founder|ceo|president|director|head|leader))',
        # Specific to the example: "It's my pleasure to introduce you to Serena Ge"
        r'(?i)(?:pleasure|happy|glad)(?:\s+to)?(?:\s+introduce)(?:\s+(?:you|to))(?:\s+to)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
    ]
    
    for pattern in intro_patterns:
        match = re.search(pattern, body)
        if match:
            other_name = match.group(1).strip()
            return other_name, ""
    
    # Try to find two names in the body and take the one that's not the sender
    names = re.findall(r'(?i)([A-Z][a-z]+(?:\\s+[A-Z][a-z]+){1,2})', body)
    current_sender_name = email_obj.get('sender_name', '')
    sender_first_name = current_sender_name.split()[0] if current_sender_name else ""
    
    # Filter out names that include the sender's first name
    if names and sender_first_name:
        for name in names:
            # Check this isn't the sender's name
            if sender_first_name.lower() not in name.lower():
                return name, ""
    
    # If no clear other person is found
    return "the other person", ""

def parse_email_from_stdin():
    """Parse an email from stdin."""
    # Read all input first to detect if it's plain text or email format
    stdin_content = sys.stdin.read()
    
    # Check if it looks like a plain text draft (no email headers)
    if not stdin_content.strip().startswith(('From:', 'To:', 'Subject:', 'Date:', 'Return-Path:')):
        # Treat as plain text draft
        return {
            'subject': '(No subject)',
            'from': '',
            'sender_name': '',
            'sender_email': '',
            'to': '',
            'cc': '',
            'date': '',
            'body': stdin_content.strip(),
            'is_introduction': False,
            'other_name': '',
            'other_email': ''
        }
    
    # Parse as email format
    from io import StringIO
    msg = email.message_from_file(StringIO(stdin_content))
    
    # Extract basic headers
    subject = decode_header(msg.get('Subject', '(No subject)'))
    from_header = msg.get('From', '')
    sender_name, sender_email = extract_name_email(from_header)
    to_header = msg.get('To', '')
    cc_header = msg.get('Cc', '')
    date = msg.get('Date', '')
    
    # Extract quoted body for context
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                try:
                    charset = part.get_content_charset() or 'utf-8'
                    payload = part.get_payload(decode=True)
                    try:
                        text = payload.decode(charset, errors='replace')
                        body = text
                        break  # We found the plain text part
                    except UnicodeDecodeError:
                        body = payload.decode('utf-8', errors='replace')
                        break
                except:
                    continue
    else:
        content_type = msg.get_content_type()
        if content_type == 'text/plain':
            try:
                charset = msg.get_content_charset() or 'utf-8'
                payload = msg.get_payload(decode=True)
                body = payload.decode(charset, errors='replace')
            except:
                body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
        elif content_type == 'text/html':
            # Very simple HTML to text conversion
            try:
                charset = msg.get_content_charset() or 'utf-8'
                html = msg.get_payload(decode=True).decode(charset, errors='replace')
                body = re.sub('<[^<]+?>', '', html)  # Remove HTML tags
            except:
                body = "(HTML content couldn't be parsed)"
    
    # Check if this is an introduction email
    is_intro = is_introduction_email(subject, body, to_header, cc_header)
    
    # Get the other person's info if this is an introduction
    other_name, other_email = "", ""
    if is_intro:
        other_name, other_email = get_other_person_info({
            'to': to_header, 
            'cc': cc_header, 
            'sender_email': sender_email, 
            'sender_name': sender_name,
            'body': body
        })
    
    # Create email object
    email_obj = {
        'subject': subject,
        'from': from_header,
        'sender_name': sender_name,
        'sender_email': sender_email,
        'to': to_header,
        'cc': cc_header,
        'date': date,
        'body': body,
        'is_introduction': is_intro,
        'other_name': other_name,
        'other_email': other_email
    }
    
    return email_obj

def generate_introduction_reply(email_obj):
    """Generate a reply for introduction emails that follows the specified format."""
    # Extract first name of sender
    sender_full_name = email_obj['sender_name']
    sender_first_name = sender_full_name.split()[0] if sender_full_name else "there"
    
    # Extract first name of other person
    other_full_name = email_obj['other_name']
    other_first_name = other_full_name.split()[0] if other_full_name else "there"
    
    # Email addresses to automatically add
    art_email = "am@theory.ventures"
    asana_email = "x@mail.asana.com"
    
    # Create the introduction reply template
    # Note: We're instructing the user to move the original sender to BCC
    # and add Art to CC and Asana to BCC
    reply = f"""Thanks {sender_first_name}, moving you to BCC.

{other_first_name}, it's a pleasure to meet you. I'm copying Art to help us find a time. Looking forward to it.

Note: Please add {art_email} to the CC field, and add {asana_email} to BCC.
"""
    
    # Clean up the reply (remove the last note - it's just for the user)
    reply = reply.replace(f"\nNote: Please add {art_email} to the CC field, and add {asana_email} to BCC.\n", "")
    
    # Print instructions for the user
    # print(f"INSTRUCTIONS: Please add {art_email} to CC and {asana_email} to BCC", file=sys.stderr)
    
    return reply

def generate_reply_with_ollama(email_obj, guidance="", intro_mode=False):
    """Generate a reply using Ollama (Gemma 3 27B) or use intro template."""
    # If this is an introduction email and intro_mode is enabled, use the template
    # But not if explicit guidance is provided
    if email_obj['is_introduction'] and intro_mode and not guidance:
        return generate_introduction_reply(email_obj)

    email_history_prompt_segment = ""
    if email_obj.get('body'):
        similar_emails_content = get_similar_emails_from_lancedb(email_obj['body'])
        if similar_emails_content:
            email_history_prompt_segment = f"""
For context, here are a few previous emails that are semantically similar to the current one. Use them to understand the topic and history of the conversation.

--- PREVIOUS SIMILAR EMAILS (FOR CONTEXT) ---
{similar_emails_content}
--- END PREVIOUS EMAILS ---

"""
        
    prompt_for_ollama = ""

    if guidance:
        current_content_to_process = guidance.strip()
        # Context from the original email body, if any, might still be useful
        original_email_context = email_obj['body'] 
        
        main_task = "Polish the DRAFT REPLY TEXT for spelling and grammar. Output only the polished text."
        
        original_word_count = len(current_content_to_process.split())
        word_limit = max(original_word_count + 2, original_word_count)  # allow small buffer
        
        prompt_for_ollama = f"""You are Tomasz Tunguz's email copy editor. Your primary goal is to polish the DRAFT REPLY TEXT for spelling, grammar, and flow, while preserving Tomasz's authentic voice.

{email_history_prompt_segment}
--- ORIGINAL EMAIL RECEIVED (for context, may be blank) ---
{original_email_context}
--- END ORIGINAL EMAIL ---

--- DRAFT REPLY TEXT (polish this) ---
{current_content_to_process}
--- END DRAFT REPLY TEXT ---

TASK: Polish the DRAFT REPLY TEXT. Your main job is to fix spelling and grammar. **Do NOT rewrite or expand the message.** Keep it exactly as casual and brief as the original.

TOMASZ'S AUTHENTIC WRITING STYLE:

**CORE CHARACTERISTICS:**
• Ultra-casual & conversational: Like texting a friend who happens to be a colleague
• Very brief: Usually 1-3 sentences, rarely more
• Natural & unpolished: "Sounds good", "I've noticed this myself", "I'll make sure to..."
• Uses contractions: "I've", "I'll", "can't", "don't"
• Simple everyday words: No corporate jargon whatsoever

**REAL EXAMPLES OF TOMASZ'S STYLE:**
• "Sounds good. I've noticed this myself."
• "I've fallen off in the last two or three weeks"
• "I will make sure to add the goals this week"
• "Great to hear from you"
• "Just let me know"

**CRITICAL RULES:**
1. **Keep it SHORT** - Don't add explanations or extra context
2. **Stay casual** - No formal business language
3. **Don't expand** - If the draft is brief, keep it brief
4. **Use simple words** - Avoid "ensure", "going forward", "emphasize the importance"
5. **Match the energy** - If it's casual, stay casual
6. **No signatures or closings** - Just the body text
7. **PRESERVE THE ORIGINAL LENGTH** - Don't make it longer

Polished Text:
"""
    else:
        # No guidance, generate a reply based on the received email.
        current_content_to_process = email_obj['body'] # This is the email received
        source_description = "--- EMAIL RECEIVED ---"
        
        main_task = "Draft a very brief, casual reply that sounds exactly like Tomasz's natural speaking voice - not formal business writing."
        
        prompt_for_ollama = f"""You are Tomasz Tunguz's AI email assistant. Draft a reply that sounds like Tomasz's natural, casual speaking voice.

{email_history_prompt_segment}
--- EMAIL RECEIVED ---
{current_content_to_process}
--- END EMAIL ---

TASK: {main_task}

TOMASZ'S NATURAL SPEAKING STYLE:

**CORE TRAITS:**
• Ultra-casual: Like a smart friend, not a business executive
• Very brief: Usually just 1-3 sentences
• Natural contractions: "I've", "I'll", "that's", "can't"
• Simple everyday words: "sounds good", "great", "thanks", "got it"
• No corporate speak: Never uses "ensure", "going forward", "circle back", "touch base"

**REAL EXAMPLES:**
• "Sounds good. I've noticed this myself."
• "Great to hear from you too!"
• "I'll start a research project on that."
• "Just let me know if you need anything."
• "Hope you're great."

**CRITICAL GUIDELINES:**
1. **Keep it VERY short** - Match the brevity of real conversations
2. **Stay super casual** - Like talking to a friend
3. **Use simple words** - No fancy business vocabulary
4. **Be warm but brief** - Friendly but not chatty
5. **NO formal endings** - No "Best regards", "Sincerely", signatures, etc.
6. **Just answer the core point** - Don't over-explain

Draft Reply:
"""

    # Call Ollama
    try:
        result = subprocess.run(
            ["ollama", "run", GENERATION_MODEL, prompt_for_ollama],
            capture_output=True,
            text=True,
            timeout=60  # Timeout after 60 seconds
        )
        
        if result.returncode != 0:
            print(f"Error generating reply: {result.stderr}", file=sys.stderr)
            return None
            
        reply_text = result.stdout.strip()
        
        # Clean up any leftover prompt artifacts
        reply_text = reply_text.replace("--- END DRAFT REPLY TEXT ---", "").strip()
        reply_text = reply_text.replace("--- END EMAIL ---", "").strip()
        reply_text = reply_text.replace("Draft Reply:", "").strip()
        reply_text = reply_text.replace("Polished Text:", "").strip()
        
        # Remove any trailing prompt markers that might leak through
        lines = reply_text.split('\n')
        cleaned_lines = []
        for line in lines:
            if not line.strip().startswith('---') and not line.strip().startswith('TASK:'):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
        
    except subprocess.TimeoutExpired:
        print(f"Timeout generating reply", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error during Ollama call: {str(e)}", file=sys.stderr)
        return None

def reformat_reply_for_lists(text_to_reformat, model_name="mistral:7b-instruct"):
    """Uses Ollama to reformat text, identifying and creating lists where appropriate."""
    if not text_to_reformat or not text_to_reformat.strip():
        return text_to_reformat

    prompt = f"""Reformat this text to use numbered lists where appropriate. Keep all original content and meaning intact. Only convert sequences like "first..., second..., third..." into numbered lists.

Example:
Input: "I have three questions. First, when will you be home? Second, what kind of spaghetti do you want? Third, when do you want to go to bed?"
Output: "I have three questions:

1. When will you be home?
2. What kind of spaghetti do you want?
3. When do you want to go to bed?"

Text to reformat:
{text_to_reformat}

Reformatted text:"""

    try:
        result = subprocess.run(
            ["ollama", "run", model_name, prompt],
            capture_output=True,
            text=True,
            timeout=45
        )
        
        if result.returncode != 0:
            return text_to_reformat
            
        reformatted_text = result.stdout.strip()
        
        # Validate the output
        if (reformatted_text and 
            len(reformatted_text) > 10 and  # Not too short
            not reformatted_text.count("I have") > 3):  # Prevent repetitive output
            return reformatted_text
        else:
            return text_to_reformat
        
    except Exception:
        return text_to_reformat

def does_text_contain_potential_list(text_to_assess, model_name="mistral:7b-instruct"):
    """Uses Mistral to assess if the text likely contains a list or list-like structure."""
    if not text_to_assess or not text_to_assess.strip():
        return False

    prompt = f"""Does the following text contain a series of distinct questions, points, or items that would benefit from list formatting?

Text: "{text_to_assess}"

Answer only YES or NO."""

    try:
        result = subprocess.run(
            ["ollama", "run", model_name, prompt],
            capture_output=True,
            text=True,
            timeout=20
        )
        
        if result.returncode != 0:
            return False
            
        assessment = result.stdout.strip().upper()
        return assessment == "YES"
        
    except Exception:
        return False

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Generate an AI reply to an email')
    parser.add_argument('--guidance', '-g', type=str, default='',
                        help='Custom guidance for how to reply to the email')
    parser.add_argument('--intro', '-i', action='store_true',
                        help='Force using the introduction reply template')
    parser.add_argument('--auto-detect', '-a', action='store_true',
                        help='Automatically detect introduction emails and use intro template')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug output')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create a log function that respects debug mode
    def log(message):
        if args.debug:
            print(message, file=sys.stderr)
    
    # Parse email from stdin
    email_obj = parse_email_from_stdin()
    
    # If auto-detect is enabled, check if this is an introduction email
    # But don't use intro mode if explicit guidance is provided
    intro_mode = args.intro or (args.auto_detect and email_obj['is_introduction'] and not args.guidance)
    
    # If we detected an introduction but don't have good "other person" info, revert to normal mode
    if intro_mode and not email_obj['other_name']:
        intro_mode = False
        print("Introduction detected but couldn't identify other person. Using normal reply.", 
              file=sys.stderr)
    
    # Print status message
    # if intro_mode:
        # print(f"Detected introduction email. Using introduction template.", file=sys.stderr)
        # if email_obj['other_name']:
            # print(f"Other person identified: {email_obj['other_name']}", file=sys.stderr)
    
    # Generate reply
    reply_text = generate_reply_with_ollama(email_obj, args.guidance, intro_mode)
    
    # Output the reply
    if reply_text:
        # print(f"DEBUG: Original reply from generate_reply_with_ollama:\\n{reply_text}", file=sys.stderr)
        
        final_reply_text = reply_text # Default to original reply

        # Only attempt list reformatting if NO explicit guidance was provided.
        # If guidance was provided, the specialized prompt in generate_reply_with_ollama
        # is expected to handle formatting (i.e., preserve existing lists, not create new ones).
        if not args.guidance:
            if does_text_contain_potential_list(reply_text, MODEL): # Ensure MODEL is used
                # print(f"DEBUG: Text contains potential list (and no guidance was given), attempting reformat.", file=sys.stderr)
                final_reply_text = reformat_reply_for_lists(reply_text, MODEL) # Ensure MODEL is used
            # else:
                # print(f"DEBUG: Text does NOT contain potential list (or guidance was given). Skipping reformat.", file=sys.stderr)
        
        # Remove automatic ampersand replacement - prompts now handle this intelligently
        # final_reply_text = re.sub(r'\\band\\b', '&', final_reply_text)
            
        # print(f"DEBUG: Final reply after potential list reformatting:\\n{final_reply_text}", file=sys.stderr)
        print(final_reply_text)
    else:
        print("Could not generate a reply. Please write your response manually.")

if __name__ == '__main__':
    main()
