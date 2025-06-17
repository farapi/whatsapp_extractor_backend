# WhatsApp Chat Extractor Backend

This FastAPI backend processes WhatsApp chat exports using Google's Gemini LLM to extract real estate property information.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
- Copy `.env.example` to `.env`
- Add your Google Gemini API key to `.env`

3. Run the server:
```bash
uvicorn main:app --reload
```

The server will run on http://localhost:8000

## API Endpoints

### POST /api/process-chat
Accepts a WhatsApp chat export file (.txt) and returns extracted property information.

Response format:
```json
[
    {
        "area": "string",
        "plot_number": "string",
        "street_width": "string",
        "orientation": "string",
        "price": "string",
        "location_link": "string",
        "raw_text": "string"
    }
]
```
