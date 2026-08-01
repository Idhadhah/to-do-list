from dotenv import load_dotenv

load_dotenv()

from ai.gemini_client import generate_text, GeminiClientError

if __name__ == "__main__":
    try:
        result = generate_text("reply with just the word hello", model="gemini-flash-latest")
        print("Success. Gemini responded with:")
        print(result)
    except GeminiClientError as e:
        print("Gemini call failed:")
        print(e)