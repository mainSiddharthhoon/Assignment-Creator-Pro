import json
import urllib.request
import urllib.error
import time
import sys
import traceback

class AIClient:
    """Client for connecting to LM Studio's local API with stability improvements."""
    def __init__(self, base_url="http://127.0.0.1:1234/v1", model="google/gemma-3-4b"):
        self.base_url = base_url
        self.model = model
        self.endpoint = f"{self.base_url}/chat/completions"

    def _trim_context(self, messages, max_messages=8, max_tokens=3000):
        """
        Trims the conversation context to fit within model limits.
        Uses a character-based heuristic (1 token approx 4 characters).
        """
        # 1. Keep only the last N messages
        trimmed = messages[-max_messages:] if len(messages) > max_messages else messages
        
        # 2. Estimate token count and further trim if needed
        # (max_tokens * 4) characters is our safe limit
        char_limit = max_tokens * 4
        
        while trimmed:
            total_chars = sum(len(m.get("content", "")) for m in trimmed)
            if total_chars <= char_limit or len(trimmed) == 1:
                break
            trimmed.pop(0) # Remove oldest message in the window
            
        return trimmed

    def get_completion(self, messages, temperature=0.7, retry_count=1):
        """
        Sends a list of messages to the local model and returns the response.
        Includes context trimming, retry logic, and extended timeouts.
        """
        # 1. Trim context before sending
        context_messages = self._trim_context(messages)
        
        data = {
            "model": self.model,
            "messages": context_messages,
            "temperature": temperature,
            "max_tokens": 600, # Initial limit for response length
            "stream": False
        }
        
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        last_error = None
        for attempt in range(retry_count + 1):
            try:
                # Use a long timeout (180s) for larger models/logical prompts
                with urllib.request.urlopen(req, timeout=180) as response:
                    res_body = response.read().decode('utf-8')
                    res_json = json.loads(res_body)
                    
                    if "choices" in res_json and len(res_json["choices"]) > 0:
                        return {
                            "success": True,
                            "content": res_json["choices"][0]["message"]["content"]
                        }
                    else:
                        raise Exception(f"Unexpected API response format: {res_json}")

            except urllib.error.URLError as e:
                last_error = f"Connection failed: {str(e.reason)}"
                print(f"--- [AIClient] Connection Attempt {attempt+1} failed: {e.reason} ---")
            except Exception as e:
                last_error = f"Processing error: {str(e)}"
                print(f"--- [AIClient] Exception on attempt {attempt+1} ---")
                traceback.print_exc()
            
            # If we're here, it failed. Wait briefly before retry if available.
            if attempt < retry_count:
                time.sleep(1) 

        return {
            "success": False,
            "error": last_error or "Unknown failure"
        }
