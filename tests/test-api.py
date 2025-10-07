import requests
import json
import os
import time
import sys

# Add project root to the Python path to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# The test script remains largely the same, as it tests the API, not the internal structure.
# It will now live in the /tests directory.

BASE_URL = "http://localhost:5009"

def create_dummy_files():
    """Create dummy files for testing if they don't exist."""
    files_to_create = {
        "sample_resume.txt": "This is a dummy resume. John Doe, Senior Software Engineer with 8 years of experience in Python and Machine Learning at Google.",
        "projects.txt": "Project Alpha: Developed a machine learning model for image recognition using TensorFlow and AWS.",
        "certifications.txt": "Certified AWS Solutions Architect. Issued by Amazon Web Services.",
        "education.txt": "University of Tech, Bachelor of Science in Computer Science, GPA 3.8. Graduated May 2016."
    }
    for filename, content in files_to_create.items():
        if not os.path.exists(filename):
            print(f"Creating dummy file: {filename}")
            with open(filename, "w") as f:
                f.write(content)

def test_complete_flow():
    """Test the complete user flow from registration to resume generation."""
    create_dummy_files()
    session = requests.Session()
    user_email = f"john.doe.{int(time.time())}@example.com"

    print("\n0. Checking service health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200 and response.json().get('status') == 'healthy':
            print("✓ Service is healthy.")
        else:
            print(f"✗ Health check failed: {response.text}")
            return
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection failed. Is the Flask app running on {BASE_URL}?")
        return

    print(f"\n1. Registering user ({user_email})...")
    response = session.post(f"{BASE_URL}/register", json={"username": "john_doe", "email": user_email})
    assert response.status_code == 201, "Registration failed"
    print("✓ Registration successful.")

    print("\n2. Uploading documents...")
    documents = ["sample_resume.txt", "projects.txt", "certifications.txt", "education.txt"]
    for filename in documents:
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "text/plain")}
            response = session.post(f"{BASE_URL}/upload-document", files=files)
            print(f"  - Uploaded {filename}: Status {response.status_code}")
            assert response.status_code == 201, f"Upload failed for {filename}"
    print("✓ All documents uploaded.")

    print("\n3. Checking user stats...")
    response = session.get(f"{BASE_URL}/stats")
    assert response.status_code == 200, "Failed to get stats"
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("✓ Stats checked.")

    print("\n4. Generating tailored resume...")
    job_description = "We are seeking a Senior Software Engineer with a background in machine learning and cloud platforms like AWS."
    response = session.post(f"{BASE_URL}/generate-resume", json={"job_description": job_description})
    
    if response.status_code == 200:
        resume = response.json().get('resume', {})
        print("✓ Resume generated successfully!")
        with open("generated_resume.json", "w") as f:
            json.dump(resume, f, indent=2)
        print("✓ Resume saved to generated_resume.json")
    else:
        print(f"✗ Resume generation failed: {response.status_code}")
        print(f"Error: {response.json()}")
    
    assert response.status_code == 200, "Resume generation failed"

    print("\n5. Logging out...")
    response = session.post(f"{BASE_URL}/logout")
    assert response.status_code == 200, "Logout failed"
    print("✓ Logged out successfully.")
    print("\n🎉 Test flow completed successfully!")

if __name__ == "__main__":
    test_complete_flow()
