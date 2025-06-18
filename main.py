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
