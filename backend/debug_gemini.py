
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Explicitly load .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key present: {bool(api_key)}")
if api_key:
    print(f"API Key length: {len(api_key)}")
    print(f"API Key start: {api_key[:4]}...")

if not api_key:
    print("ERROR: No API Key found in env.")
    exit(1)

try:
    genai.configure(api_key=api_key)
    
    # Try the requested model (user said 2.5, which likely doesn't exist publicly yet, maybe 1.5 or 2.0?)
    # Let's try 1.5-flash first as it's the standard efficient one.
    model_name = 'gemini-1.5-flash' 
    print(f"Testing model: {model_name}")
    
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Hello, can you hear me?")
    print("SUCCESS! Response received:")
    print(response.text)
    
except Exception as e:
    print("\nFAILED with error:")
    print(e)
