import os
import json
import google.generativeai as genai
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

    def clean_text_content(self, content: str) -> str:
        """Clean and prepare the text content for processing."""
        # Remove any potential Unicode BOM
        content = content.replace('\ufeff', '')
        # Basic cleaning
        return content.strip()

    def parse_whatsapp_chat(self, content: str) -> list:
        prompt = """
    Extract property information from this WhatsApp chat. For each property listing, provide:
    - Plot number
    - Area in square meters
    - Price
    - Location (if available)
    - orientation (N/S/E/W if mentioned)
    - street_width (in meters if mentioned)

    Format as JSON array like this:
    [
        {
            "plot_number": "123",
            "area": "150",
            "price": "500000",
            "location": "https://maps.google.com/"
            "orientation": "N",
            "street_width": "15",
        }
    ]
    """
    
        cleaned_content = self.clean_text_content(content)
        full_prompt = prompt + "\n\nChat content:\n" + cleaned_content
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.1,
                    "top_k": 16
                }
            )
            
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            raise
        
        # Parse the response
        try:
            response_text = response.text.strip()
            if not response_text.startswith('['):
                start = response_text.find('[')
                end = response_text.rfind(']')
                if start != -1 and end != -1:
                    response_text = response_text[start:end + 1]
                else:
                    raise ValueError(f"No JSON array found in response: {response_text}")
            
            # Parse JSON response
            properties = json.loads(response_text)
            if not isinstance(properties, list):
                raise ValueError(f"Response must be a list of properties, got {type(properties)}")
            
            return properties
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {response.text}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            print(f"Error processing response: {str(e)}")
            raise ValueError(f"Failed to process model response: {str(e)}")