import weaviate
from weaviate.classes.config import Property, DataType, Configure
from weaviate.classes.query import Filter, MetadataQuery
import hashlib
from datetime import datetime
import pypdf
import docx
import json
import uuid
from .utils import chunk_text, categorize_content

# ==============================================================================
# FILE PROCESSING SERVICE
# ==============================================================================

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        pdf_reader = pypdf.PdfReader(file)
        for page in pdf_reader.pages:
            text += (page.extract_text() or "") + "\n"
    return text

def extract_text_from_docx(file_path):
    text = ""
    doc = docx.Document(file_path)
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_text_from_file(file_path, filename):
    """Extract text based on file extension"""
    ext = filename.rsplit('.', 1)[1].lower()
    try:
        if ext == 'pdf':
            return extract_text_from_pdf(file_path)
        elif ext == 'docx':
            return extract_text_from_docx(file_path)
        elif ext == 'txt':
            return extract_text_from_txt(file_path)
        elif ext == 'json':
            with open(file_path, 'r') as f:
                return json.dumps(json.load(f), indent=2)
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
    return ""


# ==============================================================================
# WEAVIATE SERVICE
# ==============================================================================

def setup_weaviate_schema(client: weaviate.WeaviateClient):
    """Create Weaviate collections if they don't exist"""
    # FIX: The method list_all(simple=True) now returns a list of strings directly.
    # The list comprehension is no longer needed.
    collection_names = client.collections.list_all(simple=True)
    
    user_collection = "Users"
    if user_collection not in collection_names:
        client.collections.create(
            name=user_collection,
            properties=[
                Property(name="user_id", data_type=DataType.TEXT),
                Property(name="username", data_type=DataType.TEXT),
                Property(name="email", data_type=DataType.TEXT),
                Property(name="created_at", data_type=DataType.TEXT)
            ]
        )
        print(f"Created collection: {user_collection}")

    doc_collection = "UserDocuments"
    if doc_collection not in collection_names:
        client.collections.create(
            name=doc_collection,
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
            properties=[
                Property(name="user_id", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="document_id", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="filename", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="content", data_type=DataType.TEXT),
                Property(name="chunk_index", data_type=DataType.INT, skip_vectorization=True),
                Property(name="category", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="metadata", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="uploaded_at", data_type=DataType.TEXT, skip_vectorization=True)
            ]
        )
        print(f"Created collection: {doc_collection}")


def find_user_by_email(client: weaviate.WeaviateClient, collection_name: str, email: str):
    collection = client.collections.get(collection_name)
    result = collection.query.fetch_objects(
        filters=Filter.by_property("email").equal(email), limit=1
    )
    if result.objects:
        user_props = result.objects[0].properties
        return {"user_id": user_props.get("user_id"), "username": user_props.get("username")}
    return None

def add_user(client: weaviate.WeaviateClient, collection_name: str, username: str, email: str):
    user_id = hashlib.sha256(f"{username}{email}{datetime.now()}".encode()).hexdigest()[:16]
    collection = client.collections.get(collection_name)
    collection.data.insert({
        "user_id": user_id,
        "username": username,
        "email": email,
        "created_at": datetime.now().isoformat()
    })
    return {"user_id": user_id, "username": username}

def process_and_store_document(client: weaviate.WeaviateClient, collection_name: str, user_id: str, file_path: str, filename: str, category: str, metadata_str: str):
    text = extract_text_from_file(file_path, filename)
    if not text.strip():
        raise ValueError("Could not extract text from file or file is empty.")
    
    chunks = chunk_text(text)
    document_id = str(uuid.uuid4())
    collection = client.collections.get(collection_name)
    
    objects_to_insert = []
    for idx, chunk in enumerate(chunks):
        chunk_category = categorize_content(chunk) if category == 'auto' else category
        objects_to_insert.append({
            "user_id": user_id,
            "document_id": document_id,
            "filename": filename,
            "content": chunk,
            "chunk_index": idx,
            "category": chunk_category,
            "metadata": metadata_str,
            "uploaded_at": datetime.now().isoformat()
        })
    
    if objects_to_insert:
        collection.data.insert_many(objects_to_insert)

    return {
        "message": "Document uploaded successfully",
        "document_id": document_id,
        "filename": filename,
        "chunks_created": len(objects_to_insert)
    }

def get_user_documents_summary(client: weaviate.WeaviateClient, collection_name: str, user_id: str):
    collection = client.collections.get(collection_name)
    result = collection.query.fetch_objects(
        filters=Filter.by_property("user_id").equal(user_id), limit=1000
    )
    
    documents = {}
    for obj in result.objects:
        doc_id = obj.properties.get("document_id")
        if doc_id not in documents:
            documents[doc_id] = {
                "document_id": doc_id,
                "filename": obj.properties.get("filename"),
                "uploaded_at": obj.properties.get("uploaded_at"),
                "chunk_count": 0, "categories": set()
            }
        documents[doc_id]["chunk_count"] += 1
        documents[doc_id]["categories"].add(obj.properties.get("category"))
    
    return [
        {**doc, "categories": list(doc["categories"])} 
        for doc in documents.values()
    ]

def delete_document_by_id(client: weaviate.WeaviateClient, collection_name: str, user_id: str, document_id: str):
    collection = client.collections.get(collection_name)
    return collection.data.delete_many(
        where=(Filter.by_property("user_id").equal(user_id) & Filter.by_property("document_id").equal(document_id))
    )

def search_user_documents(client: weaviate.WeaviateClient, collection_name: str, user_id: str, query: str, limit: int, category_filter: str = None):
    collection = client.collections.get(collection_name)
    filters = Filter.by_property("user_id").equal(user_id)
    if category_filter:
        filters = filters & Filter.by_property("category").equal(category_filter)
    
    response = collection.query.near_text(
        query=query, filters=filters, limit=limit,
        return_metadata=MetadataQuery(distance=True)
    )
    
    results = []
    for obj in response.objects:
        props = obj.properties
        results.append({
            "content": props.get("content"),
            "category": props.get("category"),
            "filename": props.get("filename"),
            "document_id": props.get("document_id"),
            "relevance_score": 1 - obj.metadata.distance
        })
    return results

def get_user_stats(client: weaviate.WeaviateClient, collection_name: str, user_id: str):
    collection = client.collections.get(collection_name)
    agg_response = collection.aggregate.over_all(
        filters=Filter.by_property("user_id").equal(user_id),
        total_count=True
    )
    
    query_response = collection.query.fetch_objects(
        filters=Filter.by_property("user_id").equal(user_id),
        limit=10000,
        return_properties=["document_id", "category"]
    )

    documents = set()
    categories = {}
    for obj in query_response.objects:
        documents.add(obj.properties.get("document_id"))
        category = obj.properties.get("category", "general")
        categories[category] = categories.get(category, 0) + 1

    return {
        "total_documents": len(documents),
        "total_chunks": agg_response.total_count,
        "categories_by_chunk": categories
    }

# ==============================================================================
# GROQ SERVICE
# ==============================================================================

def generate_resume_from_context(groq_client, relevant_chunks, job_description):
    # Build a concise context from the most relevant chunks
    context_parts = []
    seen_content = set()
    for chunk in relevant_chunks:
        # Only include highly relevant chunks and avoid duplicates
        if chunk['relevance_score'] > 0.5 and chunk['content'] not in seen_content:
            context_parts.append(f"- {chunk['content']}")
            seen_content.add(chunk['content'])
    
    context = "\n".join(context_parts)
    if not context:
        raise ValueError("No sufficiently relevant content found.")

    prompt = f"""
You are a professional resume writer creating an ATS-optimized resume in JSON format.
Use ONLY the provided "Candidate Data" to fill out the JSON structure. Do not invent information.
Tailor the content to the "Target Job Description". If no data exists for a field, use an empty string or array.
Your entire output must be a single, valid JSON object.

**Candidate Data:**
---
{context}
---

**Target Job Description:**
---
{job_description}
---

**Required JSON Output Structure:**
{{
  "SUMMARY": "A 2-3 sentence professional summary.",
  "SKILLS": {{
    "Languages": "Comma-separated list.", "AI_ML": "Comma-separated list.", "Tools": "Comma-separated list.",
    "Database": "Comma-separated list.", "Cloud": "Comma-separated list.", "Web_Development": "Comma-separated list.",
    "Certifications": "Comma-separated list."
  }},
  "WORK_EXPERIENCE": [{{
      "Company": "Company Name", "Location": "City, State", "Title": "Job Title",
      "Dates": "Month Year - Month Year", "Bullets": ["Achievement-focused bullet point."]
  }}],
  "EDUCATION": [{{
      "Degree": "Degree and Major", "University": "University Name",
      "Relevant_Courses": ["Course 1"], "GPA": "X.X/4.0", "Dates": "Month Year"
  }}],
  "PROJECTS": [{{
      "Name": "Project Name", "Technologies": "Comma-separated list.",
      "Bullets": ["Description of project."], "Live_Demo": "URL"
  }}]
}}
"""
    completion = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=4096,
        response_format={"type": "json_object"}
    )
    
    response_content = completion.choices[0].message.content
    return json.loads(response_content)

