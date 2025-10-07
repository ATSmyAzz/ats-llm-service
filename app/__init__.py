from flask import Flask
from dotenv import load_dotenv
import os
import weaviate
from groq import Groq
from .services import setup_weaviate_schema

# Load environment variables from .env file
load_dotenv()

# Initialize external clients
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
weaviate_client = weaviate.connect_to_local(
    host=os.getenv("WEAVIATE_HOST", "localhost"),
    port=int(os.getenv("WEAVIATE_PORT", "8080")),
    grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "50051")),
)

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # Make clients available to the app context
    app.weaviate_client = weaviate_client
    app.groq_client = groq_client

    # Define constants
    app.config['UPLOAD_FOLDER'] = os.getenv("UPLOAD_FOLDER", "./uploads")
    app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt', 'json'}

    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        # Import and register routes
        from . import routes
        app.register_blueprint(routes.main_bp)

        # Setup Weaviate schema on startup
        print("Setting up Weaviate schema...")
        setup_weaviate_schema(weaviate_client)
        print("Schema setup complete.")

    return app
