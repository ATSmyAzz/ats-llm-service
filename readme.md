#ATS Resume Builder API

This project is a Flask-based API for building ATS-friendly resumes. It allows users to upload their professional documents (resumes, project descriptions, etc.), which are then stored and indexed in a Weaviate vector database. Users can then provide a job description to the API, which uses the Groq API to generate a tailored resume based on the stored documents.
Project Structure

#The project follows a standard Flask application structure to separate concerns:

/
├── app/                  # Main application source code
│   ├── __init__.py       # Initializes the Flask app and its components
│   ├── routes.py         # Defines all API endpoints (e.g., /register, /upload)
│   ├── services.py       # Contains the core business logic (Weaviate, Groq, file handling)
│   └── utils.py          # Helper functions (text chunking, categorization)
│
├── tests/                # All tests for the API
│   └── test_api.py       # The end-to-end test script
│
├── uploads/              # Temporary storage for uploaded files
│
├── .env                  # Environment variables (API keys)
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Configuration to run the Weaviate database
└── run.py                # The entry point to start the Flask application

How to Run

    Environment Variables:
    Ensure you have a .env file in the root directory with your GROQ_API_KEY.

    Start Weaviate Database:
    You need Docker installed. Run the following command in the root directory to start the Weaviate database in the background.

    docker-compose up -d

    Install Dependencies:
    It's recommended to use a virtual environment.

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    Run the Application:
    Once the dependencies are installed, start the Flask server.

    python run.py

    The API will now be running at http://localhost:5001.

    Run Tests:
    To verify that everything is working correctly, open a new terminal and run the test script.

    python -m tests.test_api

