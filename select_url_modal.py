#!/usr/bin/env python3
import sys
import email
import subprocess
from email.header import decode_header
import os
import re # Import regular expressions module

LOG_FILE = os.path.expanduser("~/.mutt/select_url_modal.log")

def write_log(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"{message}\n")

try:
    from bs4 import BeautifulSoup
except ImportError:
    write_log("ERROR: BeautifulSoup4 library not found. Please install it: pip3 install beautifulsoup4")
    sys.exit(1)

def get_body(msg, prefer_html=True):
    """Extract the body of the email, preferring HTML or plain text."""
    best_part = None
    if msg.is_multipart():
        html_part = None
        plain_part = None
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disp = part.get('Content-Disposition', '')
            if 'attachment' in content_disp.lower():
                continue

            if content_type == 'text/html':
                html_part = part
            elif content_type == 'text/plain':
                plain_part = part
        
        if prefer_html and html_part:
            best_part = html_part
        elif plain_part:
            best_part = plain_part
        elif html_part: # fallback to html if plain was preferred but not found
            best_part = html_part
    else:
        # Not multipart, so the message itself is the content
        content_type = msg.get_content_type()
        if content_type == 'text/html' or content_type == 'text/plain':
            best_part = msg

    if best_part:
        try:
            charset = best_part.get_content_charset() or 'utf-8'
            payload = best_part.get_payload(decode=True)
            return payload.decode(charset, errors='replace')
        except Exception as e:
            write_log(f"DEBUG: Error decoding part in get_body: {str(e)}")
            return None
    return None

def main():
    write_log("DEBUG: Script started (full version with regex).")
    try:
        email_content = sys.stdin.read()
    except Exception as e:
        write_log(f"DEBUG: Error reading email from stdin: {e}")
        sys.exit(1)
        
    msg = email.message_from_string(email_content)
    body_content_str = get_body(msg)
    
    if not body_content_str:
        write_log("DEBUG: No body content found by get_body.")
        sys.exit(0)
    else:
        write_log(f"DEBUG: Body content (first 300 chars): {body_content_str[:300]}")

    links_map = {}  # Using a dict {url: display_text} to auto-deduplicate by URL
    separator = " <|> " 
    
    # ANSI Color Codes for fzf list
    COLOR_LINK_TEXT = "\033[93m"  # Bright Yellow (for the orange/gold appearance)
    COLOR_URL = "\033[37m"       # Normal White (acts as Light Gray)
    COLOR_RESET = "\033[0m"

    text_for_regex_pass = body_content_str # Default, will be updated if HTML is parsed

    # Attempt 1: Parse with BeautifulSoup for <a> tags.
    # If body_content_str is plain text, BeautifulSoup won't find <a> tags but also won't typically error.
    soup = BeautifulSoup(body_content_str, 'html.parser')
    all_a_tags = soup.find_all('a', href=True)

    if all_a_tags: # If <a> tags were found, it suggests HTML content
        write_log(f"DEBUG: Found {len(all_a_tags)} <a> tags. Processing as HTML-like.")
        for a_tag in all_a_tags:
            href = a_tag['href'].strip()
            text = ' '.join(a_tag.get_text(strip=True).split()) # Get link text
            if not text: text = href # If no text, use the URL itself

            if (href.startswith('http://') or href.startswith('https://') or href.startswith('mailto:')):
                if href not in links_map: # Add if new, BeautifulSoup text takes precedence
                    links_map[href] = text
                    write_log(f"DEBUG: Added <a> link: {text} -> {href}")
            # else: write_log(f"DEBUG: Skipped <a> link with non-http/https/mailto scheme: {href}")
        
        text_for_regex_pass = soup.get_text(separator=' ') # Get all text from HTML for subsequent regex pass
        write_log("DEBUG: Using text extracted by BeautifulSoup for subsequent regex pass.")
    else:
        write_log("DEBUG: No <a> tags found by BeautifulSoup. Body will be treated as plain text for regex.")
        # text_for_regex_pass remains body_content_str

    # Attempt 2: Regex on the prepared text_for_regex_pass
    if text_for_regex_pass:
        # Regex to find URLs, trying to be robust about endings and parentheses
        url_pattern = re.compile(r'(https?://[\w\-.:/?#&%=~@\[\]!$()*+,;]+(?<![.,;:!?\\)\\]<>])|mailto:[\w\-.:@?#&%=~]+(?<![.,;:!?\\)\\]<>]))')
        found_plain_urls = url_pattern.findall(text_for_regex_pass)
        
        if found_plain_urls:
            write_log(f"DEBUG: Found {len(found_plain_urls)} potential URLs with regex.")
            processed_plain_urls_count = 0
            for url in found_plain_urls:
                # The regex now tries to exclude trailing punctuation, but a final strip can help for edge cases.
                cleaned_url = url.rstrip('.,;:!?\\)\\]<>')
                
                if (cleaned_url.startswith('http://') or cleaned_url.startswith('https://') or cleaned_url.startswith('mailto:')):
                    if cleaned_url not in links_map: # Add if new and not already found by BeautifulSoup
                        links_map[cleaned_url] = cleaned_url # Use URL as text for these plain links
                        write_log(f"DEBUG: Added regex-found link: {cleaned_url} -> {cleaned_url}")
                        processed_plain_urls_count += 1
            write_log(f"DEBUG: Added {processed_plain_urls_count} new unique URLs from regex pass.")
        else:
            write_log("DEBUG: No additional URLs found with regex in text_for_regex_pass.")
    
    # Prepare links_data for fzf from the deduplicated links_map
    links_data = []
    if not links_map:
        write_log("DEBUG: No links found by BeautifulSoup or regex. Falling back to urlscan.")
        try:
            urlscan_process = subprocess.Popen(['urlscan', '--compact'], stdin=subprocess.PIPE)
            # We don't capture output here, just let urlscan do its thing to the terminal if it runs
            urlscan_process.communicate(input=email_content.encode(), timeout=10) 
        except FileNotFoundError:
            write_log("ERROR: urlscan command not found for fallback.")
        except subprocess.TimeoutExpired:
            write_log("ERROR: urlscan fallback timed out.")
        except Exception as e:
            write_log(f"ERROR: Error during urlscan fallback: {str(e)}")
        sys.exit(0) # Exit after fallback attempt

    for href, text in links_map.items():
        display_text = (text[:75] + '...') if len(text) > 78 else text
        colored_link_entry = f"{COLOR_LINK_TEXT}{display_text}{COLOR_RESET}{separator}{COLOR_URL}{href}{COLOR_RESET}"
        links_data.append(colored_link_entry)

    fzf_input = "\n".join(links_data)
    write_log(f"DEBUG: Final input for fzf (first 300 chars): {fzf_input[:300]}")
    
    try:
        fzf_cmd = [
            'fzf', '--tac', '--height=50%', '--reverse', '--multi', '--ansi',
            '--prompt=Select URL(s) (Tab to multi-select, Enter to open)> ',
            f'--preview=echo {{}} | awk -F "{separator}" \'{{print $2}}\'',
            '--preview-window=bottom:3:wrap'
        ]
        fzf_process = subprocess.run(fzf_cmd, input=fzf_input, capture_output=True, text=True, check=False)
        write_log(f"DEBUG: fzf stdout: {fzf_process.stdout.strip()}")
        write_log(f"DEBUG: fzf stderr: {fzf_process.stderr.strip()}")
        write_log(f"DEBUG: fzf returncode: {fzf_process.returncode}")

        if fzf_process.returncode == 0 and fzf_process.stdout:
            selected_lines = fzf_process.stdout.strip().split('\n')
            write_log(f"DEBUG: fzf selected lines: {selected_lines}")
            for line in selected_lines:
                if separator in line:
                    actual_url = line.split(separator)[1]
                    write_log(f"DEBUG: Opening URL: {actual_url}")
                    subprocess.run(['open', actual_url], check=False)
        elif fzf_process.returncode == 130:
            write_log("DEBUG: fzf cancelled by user (Esc).")
        elif fzf_process.returncode == 1 and not fzf_process.stdout:
             write_log("DEBUG: fzf exited with no selection.")
        elif fzf_process.returncode != 0:
            write_log(f"ERROR: fzf returned an error (Code: {fzf_process.returncode}).")
            
    except FileNotFoundError:
        write_log("ERROR: fzf command not found. Please install fzf.")
    except Exception as e:
        write_log(f"ERROR: An unexpected error occurred in fzf handling: {str(e)}")

if __name__ == '__main__':
    main() 