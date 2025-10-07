# ATSMyAzz LLM SERVICE

**ATSMyAzz API** is a Flask-based service for creating **ATS-friendly resumes**. Users can upload professional documents (resumes, project descriptions, etc.), which are stored and indexed in a **Weaviate vector database**. Given a job description, the API leverages the **Groq API** to generate a tailored resume using the uploaded documents.

---

## Project Structure

The project follows a clean Flask structure to separate concerns:

```
/
├── app/                  # Main application source code
│   ├── __init__.py       # Initializes Flask app and components
│   ├── routes.py         # Defines API endpoints (/register, /upload, etc.)
│   ├── services.py       # Core business logic (Weaviate, Groq, file handling)
│   └── utils.py          # Helper functions (text chunking, categorization)
│
├── tests/                # Test scripts for the API
│   └── test_api.py       # End-to-end tests
│
├── uploads/              # Temporary storage for uploaded files
├── .env                  # Environment variables (API keys, DB URL, upload folder)
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker configuration for Weaviate
└── run.py                # Entry point to start the Flask application
```

---

## Environment Variables

Create a `.env` file in the root directory and define the following variables:

```env
# Supermemory API Key
SUPERMEMORY_API_KEY=

# Groq API Key
GROQ_API_KEY=

# Weaviate Database URL
WEAVIATE_URL=http://localhost:8080

# Upload folder for resumes and documents
UPLOAD_FOLDER=./uploads
```

---

## Setup and Running

### 1. Start Weaviate Database

Make sure Docker is installed. Then, in the root directory, run:

```bash
docker-compose up -d
```

This starts the **Weaviate vector database** in the background.

---

### 2. Install Dependencies

Use a Python virtual environment for isolation:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. Run the API

Start the Flask server:

```bash
python run.py
```

The API will now be available at:
[http://localhost:5001](http://localhost:5001)

---

### 4. Run Tests

Open a new terminal and run the test script:

```bash
python -m tests.test_api
```

---

## API Endpoints (Overview)

| Endpoint    | Method | Description                                        |
| ----------- | ------ | -------------------------------------------------- |
| `/register` | POST   | Register a new user                                |
| `/upload`   | POST   | Upload resumes or project documents                |
| `/generate` | POST   | Generate ATS-tailored resume using job description |

> Note: See `app/routes.py` for full details of request/response formats.

---

## Usage Example

```bash
# Upload a resume
curl -X POST http://localhost:5001/upload \
  -F "file=@resume.pdf" \
  -F "user_id=123"

# Generate a tailored resume
curl -X POST http://localhost:5001/generate \
  -H "Content-Type: application/json" \
  -d '{
        "user_id": "123",
        "job_description": "Data Analyst role at XYZ Corp"
      }'
```

---

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests to verify
5. Submit a pull request

---
