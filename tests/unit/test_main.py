"""
Unit tests for main FastAPI application
"""
import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "readme-generator"


def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    # Should return either the HTML file or a JSON message
    assert response.status_code == 200


def test_generate_with_valid_local_path():
    """Test successful README generation with a valid local path"""
    # Create a temporary directory with some files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple Python project structure
        (Path(temp_dir) / "requirements.txt").write_text("pytest>=7.0.0\nrequests>=2.28.0\n")
        (Path(temp_dir) / "main.py").write_text('"""Test application"""\nprint("Hello")')
        (Path(temp_dir) / "README.md").write_text("# Test Project")
        
        # Make the request
        response = client.post(
            "/api/generate",
            json={
                "source": temp_dir,
                "source_type": "local",
                "template": "minimal"
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "readme_content" in data
        assert len(data["readme_content"]) > 0
        assert "metadata" in data
        assert data["metadata"]["primary_language"] == "Python"
        assert data["error"] is None


def test_generate_with_invalid_local_path():
    """Test error response for invalid local path"""
    response = client.post(
        "/api/generate",
        json={
            "source": "/nonexistent/path/that/does/not/exist",
            "source_type": "local",
            "template": "detailed"
        }
    )
    
    # Should return 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Invalid local path" in data["detail"]


def test_generate_with_invalid_github_url():
    """Test error response for invalid GitHub URL"""
    response = client.post(
        "/api/generate",
        json={
            "source": "not-a-valid-url",
            "source_type": "github",
            "template": "detailed"
        }
    )
    
    # Should return 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Invalid GitHub URL" in data["detail"]


def test_generate_with_invalid_source_type():
    """Test error response for invalid source_type"""
    with tempfile.TemporaryDirectory() as temp_dir:
        response = client.post(
            "/api/generate",
            json={
                "source": temp_dir,
                "source_type": "invalid_type",
                "template": "detailed"
            }
        )
        
        # Should return 400 Bad Request
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid source_type" in data["detail"]


def test_generate_with_file_system_error():
    """Test error handling for file system errors"""
    # Try to access a path that exists but is not a directory
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = temp_file.name
    
    try:
        response = client.post(
            "/api/generate",
            json={
                "source": temp_file_path,
                "source_type": "local",
                "template": "detailed"
            }
        )
        
        # Should return 400 Bad Request (not a directory)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    finally:
        # Cleanup
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_generate_with_detailed_template():
    """Test README generation with detailed template"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a Node.js project structure
        package_json = {
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": {
                "express": "^4.18.0"
            },
            "scripts": {
                "start": "node index.js",
                "test": "jest"
            }
        }
        import json
        (Path(temp_dir) / "package.json").write_text(json.dumps(package_json))
        (Path(temp_dir) / "index.js").write_text("// Main application\nconsole.log('Hello');")
        
        response = client.post(
            "/api/generate",
            json={
                "source": temp_dir,
                "source_type": "local",
                "template": "detailed"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "readme_content" in data
        
        # Verify detailed template includes more sections
        readme = data["readme_content"]
        assert "## Installation" in readme
        assert "## Usage" in readme
        assert "## Features" in readme or "## Project Structure" in readme
        
        # Verify metadata
        assert data["metadata"]["primary_language"] == "JavaScript"
        assert data["metadata"]["template_used"] == "detailed"


def test_generate_with_minimal_template():
    """Test README generation with minimal template"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple project
        (Path(temp_dir) / "main.py").write_text("print('test')")
        
        response = client.post(
            "/api/generate",
            json={
                "source": temp_dir,
                "source_type": "local",
                "template": "minimal"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify minimal template has fewer sections
        readme = data["readme_content"]
        assert "## Installation" in readme
        assert "## Usage" in readme
        
        # Verify metadata
        assert data["metadata"]["template_used"] == "minimal"


def test_generate_with_rust_project():
    """Test README generation with Rust project"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a Rust project structure
        cargo_toml = """[package]
name = "test-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
"""
        (Path(temp_dir) / "Cargo.toml").write_text(cargo_toml)
        (Path(temp_dir) / "main.rs").write_text("fn main() { println!(\"Hello\"); }")
        
        response = client.post(
            "/api/generate",
            json={
                "source": temp_dir,
                "source_type": "local",
                "template": "detailed"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["primary_language"] == "Rust"
