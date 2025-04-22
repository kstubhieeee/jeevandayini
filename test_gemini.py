import os
from dotenv import load_dotenv
import google.generativeai as genai

def main():
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("ERROR: No API key found in environment variables!")
        return
    
    print(f"API Key starts with: {api_key[:5]}...")
    
    try:
        # Configure the API
        genai.configure(api_key=api_key)
        
        # List available models
        print("\nListing available models...")
        for model in genai.list_models():
            print(f"Found model: {model.name}")
            print(f"  Supported methods: {model.supported_generation_methods}")
        
        print("\nTrying to use gemini-pro model...")
        model = genai.GenerativeModel('gemini-pro')
        
        print("Sending test message...")
        response = model.generate_content("Hello! Can you help me understand blood donation?")
        
        print("\nResponse received!")
        print("Response text:", response.text)
        
    except Exception as e:
        print("\nError occurred!")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print("\nPlease check:")
        print("1. Your API key is correct")
        print("2. You have enabled the Gemini API in your Google Cloud Console")
        print("3. Your API key has access to the Gemini API")

if __name__ == "__main__":
    main() 