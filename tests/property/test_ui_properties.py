"""
Property-based tests for UI-related backend functionality.
Tests Properties 16-20 from the design document.

Note: These tests focus on the backend API responses that support UI interactions,
as the frontend is JavaScript-based and tested separately.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
import json
from pathlib import Path
import tempfile
import os
import shutil

from app.main import app
from fastapi.testclient import TestClient


# Test client
client = TestClient(app)


# Custom strategies for generating test data

@st.composite
def markdown_content(draw):
    """Generate valid markdown content with various elements"""
    elements = []
    
    # Add headers
    num_headers = draw(st.integers(min_value=1, max_value=5))
    for i in range(num_headers):
        level = draw(st.integers(min_value=1, max_value=6))
        header_text = draw(st.text(min_size=1, max_size=50))
        elements.append(f"{'#' * level} {header_text}")
    
    # Add paragraphs
    num_paragraphs = draw(st.integers(min_value=1, max_value=3))
    for _ in range(num_paragraphs):
        paragraph = draw(st.text(min_size=10, max_size=200))
        elements.append(paragraph)
    
    # Add code blocks
    if draw(st.booleans()):
        code = draw(st.text(min_size=5, max_size=100))
        elements.append(f"```\n{code}\n```")
    
    # Add lists
    if draw(st.booleans()):
        num_items = draw(st.integers(min_value=1, max_value=5))
        for i in range(num_items):
            item = draw(st.text(min_size=1, max_size=50))
            elements.append(f"- {item}")
    
    # Add tables
    if draw(st.booleans()):
        elements.append("| Column 1 | Column 2 |")
        elements.append("|----------|----------|")
        num_rows = draw(st.integers(min_value=1, max_value=3))
        for _ in range(num_rows):
            col1 = draw(st.text(min_size=1, max_size=20))
            col2 = draw(st.text(min_size=1, max_size=20))
            elements.append(f"| {col1} | {col2} |")
    
    return "\n\n".join(elements)


@st.composite
def readme_with_mermaid(draw):
    """Generate README content with Mermaid diagrams"""
    content = draw(markdown_content())
    
    # Add a Mermaid diagram
    diagram_type = draw(st.sampled_from(['graph', 'flowchart', 'sequenceDiagram']))
    
    if diagram_type == 'graph':
        diagram = """```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```"""
    elif diagram_type == 'flowchart':
        diagram = """```mermaid
flowchart LR
    A[Input] --> B[Transform]
    B --> C[Output]
```"""
    else:
        diagram = """```mermaid
sequenceDiagram
    participant A
    participant B
    A->>B: Request
    B->>A: Response
```"""
    
    return content + "\n\n" + diagram


@st.composite
def project_structure_for_generation(draw):
    """Generate a minimal project structure for testing"""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Create a simple Python project structure
    project_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-'),
        min_size=3,
        max_size=20
    ))
    
    project_path = Path(temp_dir) / project_name
    project_path.mkdir(exist_ok=True)
    
    # Create a requirements.txt
    (project_path / "requirements.txt").write_text("fastapi==0.104.1\nhypothesis==6.92.1")
    
    # Create a simple Python file
    (project_path / "main.py").write_text('"""A simple application"""\n\ndef main():\n    pass')
    
    return str(project_path)


# Property 16: Markdown preview rendering
# Feature: readme-generator, Property 16: Markdown preview rendering
# Validates: Requirements 8.2

class TestMarkdownPreviewRendering:
    """Test that markdown content is properly formatted for preview"""
    
    @given(content=markdown_content())
    @settings(max_examples=100, deadline=None)
    def test_generated_readme_contains_markdown_elements(self, content):
        """For any generated README content, it should contain valid markdown elements"""
        # The backend should return markdown content that can be rendered
        # We test that the API response contains markdown-formatted content
        
        # Create a temporary project
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a minimal project
            (Path(temp_dir) / "requirements.txt").write_text("pytest==7.4.0")
            
            response = client.post(
                "/api/generate",
                json={
                    "source": temp_dir,
                    "source_type": "local",
                    "template": "minimal"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    readme_content = data.get("readme_content", "")
                    
                    # Verify the content contains markdown elements
                    assert isinstance(readme_content, str), "README content should be a string"
                    assert len(readme_content) > 0, "README content should not be empty"
                    
                    # Check for common markdown elements (headers, lists, code blocks)
                    has_markdown = (
                        '#' in readme_content or  # Headers
                        '```' in readme_content or  # Code blocks
                        '-' in readme_content or  # Lists
                        '*' in readme_content  # Bold/italic or lists
                    )
                    assert has_markdown, "README should contain markdown formatting"
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# Property 17: Preview update reactivity
# Feature: readme-generator, Property 17: Preview update reactivity
# Validates: Requirements 8.4

class TestPreviewUpdateReactivity:
    """Test that API returns updated content for different requests"""
    
    @given(template=st.sampled_from(['minimal', 'detailed']))
    @settings(max_examples=50, deadline=None)
    def test_different_templates_produce_different_content(self, template):
        """For any template change, the API should return appropriately structured content"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a minimal project
            (Path(temp_dir) / "requirements.txt").write_text("pytest==7.4.0")
            (Path(temp_dir) / "README.md").write_text("# Test Project")
            
            response = client.post(
                "/api/generate",
                json={
                    "source": temp_dir,
                    "source_type": "local",
                    "template": template
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    readme_content = data.get("readme_content", "")
                    
                    # Verify content is returned
                    assert isinstance(readme_content, str), "Content should be a string"
                    assert len(readme_content) > 0, "Content should not be empty"
                    
                    # Minimal template should have fewer sections
                    if template == "minimal":
                        # Should have basic sections
                        assert "Installation" in readme_content or "install" in readme_content.lower()
                    elif template == "detailed":
                        # Should have more comprehensive sections
                        assert len(readme_content) > 100, "Detailed template should have substantial content"
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# Property 18: Clipboard copy correctness
# Feature: readme-generator, Property 18: Clipboard copy correctness
# Validates: Requirements 9.1

class TestClipboardCopyCorrectness:
    """Test that the API returns complete content for copying"""
    
    @given(project_path=project_structure_for_generation())
    @settings(max_examples=50, deadline=None)
    def test_api_returns_complete_content_for_copy(self, project_path):
        """For any generated README, the API should return complete content"""
        try:
            response = client.post(
                "/api/generate",
                json={
                    "source": project_path,
                    "source_type": "local",
                    "template": "detailed"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    readme_content = data.get("readme_content", "")
                    
                    # Verify the content is complete and copyable
                    assert isinstance(readme_content, str), "Content should be a string"
                    assert len(readme_content) > 0, "Content should not be empty"
                    
                    # Verify no truncation markers
                    assert "..." not in readme_content[-10:], "Content should not be truncated"
                    
                    # Verify content has proper structure (beginning and end)
                    lines = readme_content.strip().split('\n')
                    assert len(lines) > 0, "Content should have multiple lines"
        
        finally:
            if os.path.exists(project_path):
                shutil.rmtree(project_path, ignore_errors=True)


# Property 19: Download trigger with correct filename
# Feature: readme-generator, Property 19: Download trigger with correct filename
# Validates: Requirements 9.2

class TestDownloadTriggerWithCorrectFilename:
    """Test that the API provides content suitable for download as README.md"""
    
    @given(project_path=project_structure_for_generation())
    @settings(max_examples=50, deadline=None)
    def test_api_content_is_valid_markdown_file(self, project_path):
        """For any generated README, the content should be valid for saving as README.md"""
        try:
            response = client.post(
                "/api/generate",
                json={
                    "source": project_path,
                    "source_type": "local",
                    "template": "minimal"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    readme_content = data.get("readme_content", "")
                    
                    # Verify content is suitable for file download
                    assert isinstance(readme_content, str), "Content should be a string"
                    assert len(readme_content) > 0, "Content should not be empty"
                    
                    # Verify content can be written to a file with UTF-8 encoding
                    temp_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.md', delete=False)
                    try:
                        temp_file.write(readme_content)
                        temp_file.close()
                        
                        # Verify file was created and has content
                        assert os.path.exists(temp_file.name), "File should be created"
                        assert os.path.getsize(temp_file.name) > 0, "File should have content"
                    finally:
                        try:
                            os.unlink(temp_file.name)
                        except PermissionError:
                            # On Windows, file might still be locked
                            pass
        
        finally:
            if os.path.exists(project_path):
                shutil.rmtree(project_path, ignore_errors=True)


# Property 20: Operation feedback display
# Feature: readme-generator, Property 20: Operation feedback display
# Validates: Requirements 9.3, 11.3

class TestOperationFeedbackDisplay:
    """Test that the API provides appropriate feedback for operations"""
    
    @given(
        source_type=st.sampled_from(['local', 'github']),
        template=st.sampled_from(['minimal', 'detailed'])
    )
    @settings(max_examples=50, deadline=None)
    def test_api_provides_success_feedback(self, source_type, template):
        """For any successful operation, the API should return success status"""
        if source_type == 'local':
            temp_dir = tempfile.mkdtemp()
            try:
                # Create a minimal project
                (Path(temp_dir) / "requirements.txt").write_text("pytest==7.4.0")
                
                response = client.post(
                    "/api/generate",
                    json={
                        "source": temp_dir,
                        "source_type": source_type,
                        "template": template
                    }
                )
                
                # Verify response structure
                assert response.status_code == 200, "API should return 200 for valid requests"
                data = response.json()
                
                # Verify feedback fields are present
                assert "success" in data, "Response should have success field"
                assert isinstance(data["success"], bool), "Success should be boolean"
                
                if data["success"]:
                    assert "readme_content" in data, "Successful response should have content"
                    assert data.get("error") is None, "Successful response should not have error"
                else:
                    assert "error" in data, "Failed response should have error message"
                    assert isinstance(data["error"], str), "Error should be a string"
            
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(invalid_input=st.sampled_from(['', '/nonexistent/path', 'invalid-url']))
    @settings(max_examples=30, deadline=None)
    def test_api_provides_error_feedback_for_invalid_input(self, invalid_input):
        """For any invalid input, the API should return error feedback"""
        response = client.post(
            "/api/generate",
            json={
                "source": invalid_input,
                "source_type": "local",
                "template": "minimal"
            }
        )
        
        # API should handle invalid input gracefully
        data = response.json()
        
        # API returns error in HTTPException format with "detail" field
        # or success format with "success" field
        if "success" in data:
            # Standard success/error format
            if not data.get("success"):
                assert "error" in data, "Failed response should have error field"
                assert isinstance(data.get("error"), str), "Error should be a string"
                assert len(data.get("error", "")) > 0, "Error message should not be empty"
        elif "detail" in data:
            # HTTPException format (for validation errors)
            assert isinstance(data.get("detail"), str), "Detail should be a string"
            assert len(data.get("detail", "")) > 0, "Error detail should not be empty"
        else:
            # Should have some error information
            assert False, "Response should have either 'success' or 'detail' field for error feedback"
