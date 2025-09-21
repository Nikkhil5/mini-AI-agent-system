import requests
from typing import Tuple, Optional
import trafilatura
from pypdf import PdfReader
from io import BytesIO
import time

# Enhanced headers for better web scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Research-Agent/1.0; +https://example.com/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def fetch_url(url: str, timeout: int = 30) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    Fetch URL and return (content_bytes, content_type, error)
    Enhanced with better error handling and retries
    """
    if not url or not url.startswith(('http://', 'https://')):
        return None, None, "Invalid URL format"

    # Add retry logic
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            # Use session for better connection handling
            session = requests.Session()
            session.headers.update(HEADERS)

            response = session.get(
                url, 
                timeout=timeout, 
                stream=True,
                allow_redirects=True,
                verify=True  # SSL verification
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()

            # Check content length to avoid huge downloads
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > 50 * 1024 * 1024:  # 50MB limit
                return None, None, "Content too large (>50MB)"

            # Read content with size limit
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > 50 * 1024 * 1024:  # 50MB limit
                    return None, None, "Content too large during download"

            return content, content_type, None

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(1)  # Brief delay before retry
                continue
            return None, None, f"Timeout after {timeout}s (tried {max_retries + 1} times)"

        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                time.sleep(1)
                continue
            return None, None, "Connection failed"

        except requests.exceptions.HTTPError as e:
            return None, None, f"HTTP error: {e.response.status_code}"

        except requests.exceptions.RequestException as e:
            return None, None, f"Request error: {str(e)}"

        except Exception as e:
            return None, None, f"Unexpected error: {str(e)}"

    return None, None, "All retry attempts failed"

def extract_text_from_html(html_bytes: bytes, url: str) -> str:
    """
    Use trafilatura to extract and clean text with fallback methods
    """
    if not html_bytes:
        return ""

    try:
        # Primary method: Use trafilatura with HTML bytes
        html_string = html_bytes.decode('utf-8', errors='ignore')
        extracted = trafilatura.extract(
            html_string,
            include_comments=False,
            include_tables=True,  # Include tables for better content
            include_images=False,
            favor_precision=True,
            url=url
        )

        if extracted and len(extracted.strip()) > 100:
            return extracted.strip()

        # Fallback 1: Try with URL directly
        extracted = trafilatura.extract(
            trafilatura.fetch_url(url),
            include_comments=False,
            include_tables=True,
            favor_precision=True
        )

        if extracted and len(extracted.strip()) > 100:
            return extracted.strip()

        # Fallback 2: Basic text extraction from HTML
        from html import unescape
        import re

        # Remove script and style elements
        html_string = re.sub(r'<script.*?</script>', '', html_string, flags=re.DOTALL | re.IGNORECASE)
        html_string = re.sub(r'<style.*?</style>', '', html_string, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_string)
        text = unescape(text)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text if len(text) > 100 else ""

    except Exception as e:
        print(f"HTML extraction error for {url}: {e}")
        return ""

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes with better error handling
    """
    if not pdf_bytes:
        return ""

    try:
        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PdfReader(pdf_file)

        if len(pdf_reader.pages) == 0:
            return ""

        # Limit to first 10 pages to avoid processing huge PDFs
        max_pages = min(10, len(pdf_reader.pages))
        text_parts = []

        for page_num in range(max_pages):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()

                if page_text and page_text.strip():
                    text_parts.append(page_text.strip())

            except Exception as e:
                print(f"Error extracting page {page_num}: {e}")
                continue

        full_text = "\n\n".join(text_parts)

        # Clean up the text
        import re
        # Remove excessive whitespace
        full_text = re.sub(r'\s+', ' ', full_text)
        full_text = re.sub(r'\n\s*\n\s*\n', '\n\n', full_text)

        return full_text.strip()

    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

def get_content_preview(content: str, max_length: int = 200) -> str:
    """
    Get a preview of content for logging/debugging
    """
    if not content:
        return "No content"

    content = content.strip()
    if len(content) <= max_length:
        return content

    return content[:max_length] + "..."

def validate_extracted_content(content: str, min_length: int = 100) -> bool:
    """
    Validate if extracted content is useful
    """
    if not content or not isinstance(content, str):
        return False

    content = content.strip()

    # Check minimum length
    if len(content) < min_length:
        return False

    # Check if content is mostly meaningful (not just whitespace/punctuation)
    import re
    words = re.findall(r'\b\w+\b', content)
    if len(words) < 20:  # At least 20 words
        return False

    # Check for common error pages/messages
    error_indicators = [
        'page not found', '404', '403 forbidden', 'access denied',
        'javascript is disabled', 'enable javascript', 'captcha',
        'blocked', 'bot detection'
    ]

    content_lower = content.lower()
    if any(indicator in content_lower for indicator in error_indicators):
        return False

    return True
