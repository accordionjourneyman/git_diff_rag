#!/usr/bin/env python3
"""scripts/call_gemini.py - Gemini API with specific error handling"""
import os, sys, time
from google import genai
from google.api_core import exceptions
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview')
MAX_RETRIES = 3

def get_client(api_key=None):
    key = api_key or os.environ.get('GEMINI_API_KEY')
    if not key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    return genai.Client(api_key=key)

def list_models(client=None):
    if client is None:
        client = get_client()
    try:
        # Filter for generateContent capable models if possible, or just return all
        # For now, we'll return all and let the user pick, or filter by 'gemini'
        models = []
        for m in client.models.list():
            if 'gemini' in m.name:
                models.append(m.name.replace('models/', ''))
        return sorted(models)
    except Exception as e:
        print(f"[WARN] Failed to list models: {e}", file=sys.stderr)
        return []

def count_tokens(prompt: str, client=None, model=None):
    if client is None:
        client = get_client()
    target_model = model or MODEL
    try:
        response = client.models.count_tokens(model=target_model, contents=prompt)
        return response.total_tokens
    except Exception as e:
        raise RuntimeError(f"Token counting failed: {e}")

def call_with_retry(prompt: str, client=None, model=None) -> str:
    if not prompt.strip():
        raise ValueError("Empty prompt")
    
    if client is None:
        client = get_client()
    
    target_model = model or MODEL
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(model=target_model, contents=prompt)
            return response.text
        except exceptions.InvalidArgument as e:
            raise ValueError(f"Invalid Argument (prompt issue?): {e}")
        except exceptions.Unauthenticated as e:
            raise PermissionError(f"API Key Invalid: {e}")
        except (exceptions.ResourceExhausted, exceptions.ServiceUnavailable) as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"[WARN] {type(e).__name__}, retry in {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise RuntimeError(f"Max retries: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: call_gemini.py [--count-tokens] <prompt_file> [output_file]")
        sys.exit(1)

    if sys.argv[1] == '--count-tokens':
        if len(sys.argv) < 3:
             print("Usage: call_gemini.py --count-tokens <prompt_file>")
             sys.exit(1)
        try:
            with open(sys.argv[2], 'r', encoding='utf-8') as f:
                prompt = f.read()
            tokens = count_tokens(prompt)
            print(f"Estimated Tokens: {tokens}")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)
        
    if len(sys.argv) < 3:
        print("Usage: call_gemini.py <prompt_file> <output_file>")
        sys.exit(1)
        
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            prompt = f.read()
        result = call_with_retry(prompt)
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            f.write(result)
    except Exception as e:
        print(f"[FATAL] {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
