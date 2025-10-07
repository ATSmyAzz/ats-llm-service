def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def chunk_text(text, chunk_size=500, overlap=100):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at a natural sentence boundary
        if end < text_length:
            last_period = chunk.rfind('.')
            if last_period > chunk_size * 0.7:  # Only break if it's near the end
                chunk = chunk[:last_period + 1]
                end = start + last_period + 1
        
        stripped_chunk = chunk.strip()
        if stripped_chunk:
            chunks.append(stripped_chunk)
            
        start = end - overlap if end - overlap > start else start + len(chunk)
        if start >= text_length: break

    return chunks

def categorize_content(content):
    """Automatically categorize content based on keywords"""
    content_lower = content.lower()
    categories = {
        'education': ['university', 'college', 'degree', 'bachelor', 'master', 'phd', 'gpa'],
        'experience': ['company', 'worked', 'position', 'role', 'responsibilities', 'achieved', 'led'],
        'skills': ['proficient', 'experienced in', 'skills:', 'technologies:', 'programming', 'languages:'],
        'projects': ['project', 'developed', 'built', 'created', 'implemented', 'github'],
        'certifications': ['certified', 'certification', 'certificate', 'credential']
    }
    
    scores = {cat: sum(1 for kw in kws if kw in content_lower) for cat, kws in categories.items()}
    
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return 'general'
