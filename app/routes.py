from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime

from .services import (
    find_user_by_email, add_user, process_and_store_document, 
    get_user_documents_summary, delete_document_by_id, search_user_documents,
    generate_resume_from_context, get_user_stats
)
from .utils import allowed_file

# Create a Blueprint
main_bp = Blueprint('main', __name__)

USER_COLLECTION = "Users"
DOCUMENT_COLLECTION = "UserDocuments"

# ==================== USER MANAGEMENT ====================

@main_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    
    if not username or not email:
        return jsonify({"error": "Username and email are required"}), 400
    
    client = current_app.weaviate_client
    
    if find_user_by_email(client, USER_COLLECTION, email):
        return jsonify({"error": "User with this email already exists"}), 409
    
    user = add_user(client, USER_COLLECTION, username, email)
    if not user:
        return jsonify({"error": "Registration failed"}), 500
        
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    
    return jsonify({
        "message": "User registered successfully",
        "user_id": user['user_id'],
        "username": user['username']
    }), 201

@main_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    client = current_app.weaviate_client
    user = find_user_by_email(client, USER_COLLECTION, email)
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    session['user_id'] = user['user_id']
    session['username'] = user['username']
    
    return jsonify({"message": "Login successful", **user}), 200

@main_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@main_bp.route('/current-user', methods=['GET'])
def current_user():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"user_id": session['user_id'], "username": session['username']}), 200

# ==================== DOCUMENT MANAGEMENT ====================

@main_bp.route('/upload-document', methods=['POST'])
def upload_document():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
        
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        return jsonify({"error": "Invalid file or file type"}), 400

    user_id = session['user_id']
    filename = secure_filename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{user_id}_{filename}")
    file.save(file_path)

    category = request.form.get('category', 'auto')
    metadata_str = request.form.get('metadata', '{}')
    
    try:
        result = process_and_store_document(
            client=current_app.weaviate_client,
            collection_name=DOCUMENT_COLLECTION,
            user_id=user_id,
            file_path=file_path,
            filename=filename,
            category=category,
            metadata_str=metadata_str
        )
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": f"Failed to process document: {str(e)}"}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@main_bp.route('/my-documents', methods=['GET'])
def my_documents():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    documents = get_user_documents_summary(
        client=current_app.weaviate_client,
        collection_name=DOCUMENT_COLLECTION,
        user_id=session['user_id']
    )
    return jsonify({"documents": documents, "total": len(documents)}), 200

@main_bp.route('/delete-document/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    response = delete_document_by_id(
        client=current_app.weaviate_client,
        collection_name=DOCUMENT_COLLECTION,
        user_id=session['user_id'],
        document_id=document_id
    )
    
    if response.successful == 0 and response.failed == 0:
         return jsonify({"error": "Document not found"}), 404
    
    return jsonify({
        "message": "Document deletion initiated",
        "successful_deletes": response.successful,
        "failed_deletes": response.failed
    }), 200

@main_bp.route('/search-my-documents', methods=['POST'])
def search_my_documents():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400

    results = search_user_documents(
        client=current_app.weaviate_client,
        collection_name=DOCUMENT_COLLECTION,
        user_id=session['user_id'],
        query=query,
        limit=data.get('limit', 20),
        category_filter=data.get('category')
    )
    return jsonify({"results": results, "count": len(results)}), 200

# ==================== RESUME GENERATION ====================

@main_bp.route('/generate-resume', methods=['POST'])
def generate_resume():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    job_description = data.get('job_description', '').strip()
    if not job_description:
        return jsonify({"error": "Job description is required"}), 400

    # 1. Fetch relevant context from Weaviate
    relevant_chunks = search_user_documents(
        client=current_app.weaviate_client,
        collection_name=DOCUMENT_COLLECTION,
        user_id=session['user_id'],
        query=job_description,
        limit=30
    )
    
    if not relevant_chunks:
        return jsonify({"error": "No relevant documents found to build a resume."}), 404
        
    # 2. Generate resume using Groq
    try:
        resume_json = generate_resume_from_context(
            groq_client=current_app.groq_client,
            relevant_chunks=relevant_chunks,
            job_description=job_description
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate resume: {str(e)}"}), 500

    return jsonify({
        "message": "Resume generated successfully",
        "resume": resume_json,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "user_id": session['user_id'],
            "sources_used": len(relevant_chunks)
        }
    }), 200

# ==================== UTILITIES ====================

@main_bp.route('/health', methods=['GET'])
def health():
    try:
        live = current_app.weaviate_client.is_live()
        if not live: raise Exception("Weaviate is not live")
        return jsonify({"status": "healthy", "weaviate": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@main_bp.route('/stats', methods=['GET'])
def stats():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
        
    statistics = get_user_stats(
        client=current_app.weaviate_client,
        collection_name=DOCUMENT_COLLECTION,
        user_id=session['user_id']
    )
    return jsonify({
        "user_id": session['user_id'],
        "username": session.get('username'),
        **statistics
    }), 200
