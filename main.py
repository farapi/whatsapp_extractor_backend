from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from zip_handler import ZipFileHandler
from gemini_service import GeminiService

app = FastAPI()

# Initialize services
gemini_service = GeminiService()

@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "ok"}, status_code=200)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"Error processing request: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"An error occurred: {str(exc)}"},
    )

# Test the Gemini service connection
try:
    print("\nTesting Gemini API connection...")
    response = gemini_service.model.generate_content("Hello, are you working?")
    print(f"API Test Response: {response.text}")
    print("Gemini API connection successful!")
except Exception as e:
    print(f"Error testing Gemini API: {str(e)}")
    raise

def clean_text_content(content: str) -> str:
    """Clean and prepare the text content for processing."""
    # Remove any null bytes or invalid characters
    content = content.replace('\x00', '')
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    return content

def retry_generate_content(prompt: str, max_retries: int = 3):
    """Retry the generate_content call with exponential backoff."""
    import time
    for attempt in range(max_retries):
        try:
            response = gemini_service.model.generate_content(prompt)
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) * 1  # Exponential backoff: 1, 2, 4 seconds
            print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

import json

def parse_whatsapp_chat(content: str):
    prompt = """
    You are a real estate data extractor. Analyze this WhatsApp chat content and extract property listings information.
    For each property listing found, extract these fields (if available):
    - area (in square meters if mentioned)
    - plot_number (any plot or lot number mentioned)
    - street_width (in meters if mentioned)
    - orientation (N/S/E/W if mentioned)
    - price (numbers only, no currency symbols)
    - location_link (any Google Maps or location link)
    - raw_text (the complete original message)

    IMPORTANT: You must respond ONLY with a valid JSON array. Do not include any other text.
    Use this exact format, with all values as strings:
    [
        {
            "area": "150",
            "plot_number": "123",
            "street_width": "15",
            "orientation": "N",
            "price": "500000",
            "location_link": "https://maps...",
            "raw_text": "original message here"
        }
    ]

    Rules:
    1. ALL values must be strings (use quotes)
    2. Use null for missing values
    3. Remove any currency symbols or commas from prices
    4. Convert Arabic numerals to English numerals
    5. Respond ONLY with the JSON array, no other text
    """
    
    # Clean the content first
    cleaned_content = clean_text_content(content)
    
    # Prepare the complete prompt with the content
    full_prompt = prompt + "\n\nChat content:\n" + cleaned_content
    
    # Try to generate content with retries
    try:
        # Generate content with safety settings
        safety_settings = {
            "HARASSMENT": "block_none",
            "HATE_SPEECH": "block_none",
            "SEXUALLY_EXPLICIT": "block_none",
            "DANGEROUS_CONTENT": "block_none"
        }
        
        response = gemini_service.model.generate_content(
            prompt + "\n\nChat content:\n" + cleaned_content,
            generation_config={
                "temperature": 0.1,  # More deterministic
                "top_p": 0.1,      # More focused
                "top_k": 16        # Limited vocabulary
            }
        )
        
        print(f"Raw model response: {response.text}")
        
        # Clean the response text
        response_text = response.text.strip()
        if not response_text.startswith('['):
            # Find the first '[' and the last ']'
            start = response_text.find('[')
            end = response_text.rfind(']')
            if start != -1 and end != -1:
                response_text = response_text[start:end + 1]
            else:
                raise ValueError(f"No JSON array found in response: {response_text}")
        
        print(f"Cleaned response text: {response_text}")
        
        # Parse and validate JSON
        try:
            properties = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            print(f"Problematic text: {response_text}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        
        if not isinstance(properties, list):
            raise ValueError(f"Response must be a list of properties, got {type(properties)}")
        
        # Process each property
        processed_properties = []
        for prop in properties:
            if not isinstance(prop, dict):
                print(f"Skipping non-dict property: {prop}")
                continue
                
            # Create a new property with all required fields
            processed_prop = {
                'area': str(prop.get('area', '')) or None,
                'plot_number': str(prop.get('plot_number', '')) or None,
                'street_width': str(prop.get('street_width', '')) or None,
                'orientation': str(prop.get('orientation', '')) or None,
                'price': str(prop.get('price', '')) or None,
                'location_link': str(prop.get('location_link', '')) or None,
                'raw_text': str(prop.get('raw_text', '')) or None
            }
            
            # Clean up price (remove commas and currency symbols)
            if processed_prop['price']:
                processed_prop['price'] = ''.join(c for c in processed_prop['price'] if c.isdigit())
            
            processed_properties.append(processed_prop)
        
        print(f"Successfully processed {len(processed_properties)} properties")
        return processed_properties
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {response.text}")
        raise ValueError(f"Invalid JSON response from model: {str(e)}")
    except Exception as e:
        print(f"Error processing response: {str(e)}\nResponse: {response.text if 'response' in locals() else 'No response generated'}")
        raise ValueError(f"Failed to process model response: {str(e)}")

@app.post("/process-chat")
async def process_chat(file: UploadFile):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Please upload a zip file")

    temp_zip_path = None
    zip_handler = None

    try:
        # Save the uploaded zip file temporarily
        temp_zip_path = f"temp_{file.filename}"
        with open(temp_zip_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)

        # Process the zip file
        zip_handler = ZipFileHandler(temp_zip_path)
        
        # Get the chat file
        chat_file_path = zip_handler.get_chat_file()
        if not chat_file_path:
            raise HTTPException(status_code=400, detail="No chat file found in the zip")

        # Read the chat file content
        with open(chat_file_path, 'r', encoding='utf-8') as f:
            chat_content = f.read()

        # Parse and analyze the chat using Gemini
        properties = gemini_service.parse_whatsapp_chat(chat_content)
        
        return {"properties": properties}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Ensure cleanup happens no matter what
        if zip_handler:
            zip_handler.cleanup()
        if temp_zip_path and os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
