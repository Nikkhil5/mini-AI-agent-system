import os
import json
from typing import List, Dict, Any
from search_tool import serpapi_search
from extractor import fetch_url, extract_text_from_html, extract_text_from_pdf_bytes
from db import save_report
import time

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
client = None

def get_openai_client():
    global client
    if client is None and OPENAI_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_KEY)
            print("✅ OpenAI client initialized successfully")
        except Exception as e:
            print(f"❌ OpenAI initialization failed: {e}")
            client = False  # Mark as failed to avoid retry
    return client if client is not False else None

def summarize_with_openai(sources: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """
    Build a structured prompt and call OpenAI ChatCompletion to make a report.
    Returns a dict with title, summary, key_points, references, raw_prompt_response.
    """
    openai_client = get_openai_client()
    
    if not openai_client:
        # Fallback summary when OpenAI is not available
        return create_fallback_summary(sources, query)

    # Dynamic content allocation based on number of sources
    max_content_per_source = min(3000, 12000 // max(1, len(sources)))
    
    system = (
        "You are a concise research assistant. Given a user query and extracted source texts, "
        "produce a short structured report: Title, Short summary (2-3 sentences), 4-6 bullet key points, "
        "and References (list of URLs with short 6-10 word note). Keep the report factual and cite only the provided "
        "sources. Respond in valid JSON format with keys: title, summary, key_points (array), references (array of {url, note})."
    )

    source_texts = ""
    for i, src in enumerate(sources, 1):
        content = src.get("content", "")[:max_content_per_source]
        source_texts += f"\n\n--- SOURCE {i}: {src['title']} ({src['url']}) ---\n{content}"

    user_prompt = f"Query: {query}\n\nSources:{source_texts}\n\nProvide a structured JSON report:"

    try:
        # Use modern OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # More cost-effective model
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        raw_response = response.choices[0].message.content.strip()
        
        # Try to parse JSON response
        try:
            report_data = json.loads(raw_response)
            
            # Validate required fields
            required_fields = ['title', 'summary', 'key_points', 'references']
            if all(field in report_data for field in required_fields):
                return {
                    "title": report_data["title"],
                    "summary": report_data["summary"],
                    "key_points": report_data["key_points"],
                    "references": report_data["references"],
                    "raw_prompt_response": raw_response
                }
        except json.JSONDecodeError:
            pass
        
        # Fallback parsing for non-JSON responses
        return parse_text_response(raw_response, query)
        
    except Exception as e:
        print(f"❌ OpenAI API call failed: {e}")
        return create_fallback_summary(sources, query)

def create_fallback_summary(sources: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """Create a fallback summary when OpenAI is not available"""
    return {
        "title": f"Research Report: {query}",
        "summary": f"Found {len(sources)} sources related to '{query}'. This report was generated using content extraction and analysis of web sources.",
        "key_points": [
            f"Successfully searched for: {query}",
            f"Retrieved {len(sources)} relevant sources",
            "Content extracted from web pages",
            "Sources include academic and news articles" if len(sources) > 1 else "Single source analyzed",
            "Data compiled from recent web content"
        ][:5],
        "references": [
            {
                "url": src.get("url", ""),
                "note": src.get("title", "")[:60] + "..." if len(src.get("title", "")) > 60 else src.get("title", "")
            } for src in sources
        ],
        "raw_prompt_response": "Fallback summary generated without OpenAI"
    }

def parse_text_response(raw_response: str, query: str) -> Dict[str, Any]:
    """Parse non-JSON OpenAI response"""
    lines = raw_response.split("\n")
    title = f"Research Report: {query}"
    summary = ""
    key_points = []
    references = []
    
    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if "title:" in line.lower() or line.startswith("#"):
            title = line.replace("Title:", "").replace("#", "").strip()
        elif "summary:" in line.lower():
            current_section = "summary"
            summary = line.replace("Summary:", "").strip()
        elif "key points:" in line.lower() or "key_points:" in line.lower():
            current_section = "key_points"
        elif "references:" in line.lower():
            current_section = "references"
        elif current_section == "summary" and summary:
            summary += " " + line
        elif current_section == "key_points" and (line.startswith("-") or line.startswith("•")):
            key_points.append(line.lstrip("-• "))
        elif current_section == "references" and (line.startswith("-") or line.startswith("•")):
            references.append({"url": "N/A", "note": line.lstrip("-• ")})
    
    return {
        "title": title or f"Research Report: {query}",
        "summary": summary or "Summary not available from parsed response",
        "key_points": key_points if key_points else ["No key points extracted from response"],
        "references": references,
        "raw_prompt_response": raw_response
    }

def run_agent_for_query(query: str) -> Dict[str, Any]:
    """
    Main agent orchestration: search -> extract -> summarize -> save
    """
    start_time = time.time()
    print(f"🔍 Starting research for: {query}")
    
    # Step 1: Search for sources
    try:
        print("🌐 Searching with SerpAPI...")
        search_results = serpapi_search(query, num_results=3)
        if not search_results:
            return {
                "success": False, 
                "error": "No search results found",
                "report_id": None
            }
        print(f"✅ Found {len(search_results)} search results")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return {
            "success": False, 
            "error": f"Search failed: {str(e)}",
            "report_id": None
        }

    # Step 2: Extract content from sources
    print("📄 Extracting content from sources...")
    sources = []
    skipped_sources = []
    
    for i, result in enumerate(search_results, 1):
        url = result["link"]
        title = result["title"]
        print(f"  Processing source {i}/{len(search_results)}: {title[:50]}...")
        
        # Validate URL
        if not is_valid_url(url):
            skipped_sources.append({
                "url": url, 
                "title": title, 
                "reason": "Blocked domain"
            })
            continue
            
        try:
            content_bytes, content_type, error = fetch_url(url)
            
            if error:
                skipped_sources.append({
                    "url": url, 
                    "title": title, 
                    "reason": f"Fetch error: {error}"
                })
                continue
                
            # Extract text based on content type
            content_text = ""
            if content_type and "pdf" in content_type:
                content_text = extract_text_from_pdf_bytes(content_bytes)
            else:
                content_text = extract_text_from_html(content_bytes, url)
            
            if content_text and len(content_text.strip()) > 100:
                # Cap content at 30K characters for performance
                content_text = content_text[:30000]
                sources.append({
                    "url": url,
                    "title": title,
                    "content": content_text
                })
                print(f"  ✅ Extracted {len(content_text)} characters")
            else:
                skipped_sources.append({
                    "url": url, 
                    "title": title, 
                    "reason": "Insufficient content extracted"
                })
                print(f"  ⚠️ Skipped: insufficient content")
                
        except Exception as e:
            skipped_sources.append({
                "url": url, 
                "title": title, 
                "reason": f"Processing error: {str(e)}"
            })
            print(f"  ❌ Error: {str(e)}")
    
    if not sources:
        return {
            "success": False,
            "error": "No content could be extracted from any source",
            "skipped_sources": skipped_sources,
            "report_id": None
        }
    
    print(f"✅ Successfully extracted content from {len(sources)} sources")
    
    # Step 3: Generate summary
    try:
        print("🤖 Generating summary...")
        report = summarize_with_openai(sources, query)
        print("✅ Summary generated successfully")
    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        return {
            "success": False,
            "error": f"Summarization failed: {str(e)}",
            "sources_found": len(sources),
            "skipped_sources": skipped_sources,
            "report_id": None
        }
    
    # Step 4: Save to database
    try:
        print("💾 Saving to database...")
        report_obj = {
            "query": query,
            "sources": sources,
            "skipped_sources": skipped_sources,
            "report": report,
            "processing_time": round(time.time() - start_time, 2)
        }
        
        report_id = save_report(
            query=query,
            title=report["title"],
            summary=report["summary"],
            report_obj=report_obj
        )
        
        print(f"✅ Report saved with ID: {report_id}")
        print(f"⏱️ Total processing time: {report_obj['processing_time']}s")
        
        return {
            "success": True,
            "report_id": report_id,
            "sources_found": len(sources),
            "skipped_sources": skipped_sources,
            "processing_time": report_obj["processing_time"]
        }
        
    except Exception as e:
        print(f"❌ Database save failed: {e}")
        return {
            "success": False,
            "error": f"Database save failed: {str(e)}",
            "sources_found": len(sources),
            "skipped_sources": skipped_sources,
            "report_id": None
        }

def is_valid_url(url: str) -> bool:
    """
    Filter out problematic domains and file types
    """
    blocked_domains = [
        'youtube.com', 'youtu.be', 'twitter.com', 'x.com',
        'facebook.com', 'instagram.com', 'linkedin.com',
        'reddit.com', 'tiktok.com'
    ]
    
    blocked_extensions = ['.mp4', '.mp3', '.jpg', '.png', '.gif', '.zip', '.exe']
    
    url_lower = url.lower()
    
    # Check blocked domains
    if any(domain in url_lower for domain in blocked_domains):
        return False
        
    # Check blocked file extensions
    if any(ext in url_lower for ext in blocked_extensions):
        return False
        
    return True

# Test the agent if run directly
if __name__ == "__main__":
    test_query = "latest AI developments 2024"
    print(f"Testing agent with query: {test_query}")
    result = run_agent_for_query(test_query)
    print("\nResult:")
    print(json.dumps(result, indent=2))
