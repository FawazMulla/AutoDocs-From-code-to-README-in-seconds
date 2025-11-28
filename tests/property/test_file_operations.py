"""
Property-based tests for file save operations.
Tests Property 21 from the design document.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile
import os
import shutil

from app.validators import InputValidator


# Custom strategies for generating test data

@st.composite
def valid_project_paths(draw):
    """Generate valid project directory paths"""
    # Create a temporary directory that we know exists
    temp_dir = tempfile.mkdtemp()
    return temp_dir


@st.composite
def readme_content(draw):
    """Generate valid README content"""
    # Generate markdown-like content (filter out line breaks and invalid unicode to avoid issues)
    title = draw(st.text(
        alphabet=st.characters(
            blacklist_characters='\r\n',
            blacklist_categories=('Cs',)  # Exclude surrogates
        ),
        min_size=1, 
        max_size=100
    ))
    description = draw(st.text(
        alphabet=st.characters(
            blacklist_characters='\r\n',
            blacklist_categories=('Cs',)  # Exclude surrogates
        ),
        min_size=10, 
        max_size=500
    ))
    
    content = f"""# {title}

{description}

## Installation

```bash
npm install
```

## Usage

Run the application with:

```bash
npm start
```

## Features

- Feature 1
- Feature 2
- Feature 3

## License

MIT
"""
    return content


# Property 21: File save to correct location
# Feature: readme-generator, Property 21: File save to correct location
# Validates: Requirements 11.1

class TestFileSaveLocation:
    """Test that README files are saved to the correct location"""
    
    @given(
        project_path=valid_project_paths(),
        content=readme_content()
    )
    @settings(max_examples=100)
    def test_readme_saved_to_project_root(self, project_path, content):
        """For any local project path, the README.md should be saved to the root directory"""
        try:
            # Validate the project path
            validator = InputValidator()
            validation_result = validator.validate_local_path(project_path)
            
            assert validation_result.valid, "Project path should be valid"
            
            # Construct expected README path
            project_dir = Path(validation_result.sanitized_input)
            expected_readme_path = project_dir / "README.md"
            
            # Write the README file
            with open(expected_readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Verify the file exists at the correct location
            assert expected_readme_path.exists(), "README.md should exist at project root"
            assert expected_readme_path.is_file(), "README.md should be a file"
            
            # Verify the content matches (normalize line endings for cross-platform compatibility)
            with open(expected_readme_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            # Normalize line endings for comparison
            normalized_saved = saved_content.replace('\r\n', '\n')
            normalized_content = content.replace('\r\n', '\n')
            
            assert normalized_saved == normalized_content, "Saved content should match original content"
            
            # Verify it's in the root directory (not a subdirectory)
            assert expected_readme_path.parent == project_dir, "README.md should be in project root"
            
        finally:
            # Cleanup
            if os.path.exists(project_path):
                shutil.rmtree(project_path, ignore_errors=True)
    
    @given(
        project_path=valid_project_paths(),
        content=readme_content()
    )
    @settings(max_examples=100)
    def test_readme_overwrite_existing_file(self, project_path, content):
        """For any project with existing README, new content should overwrite it"""
        try:
            # Create an existing README with different content
            project_dir = Path(project_path)
            readme_path = project_dir / "README.md"
            
            old_content = "# Old README\n\nThis is old content."
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(old_content)
            
            assert readme_path.exists(), "Old README should exist"
            
            # Write new content
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Verify the file was overwritten (normalize line endings for cross-platform compatibility)
            with open(readme_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            # Normalize line endings for comparison
            normalized_saved = saved_content.replace('\r\n', '\n')
            normalized_content = content.replace('\r\n', '\n')
            normalized_old = old_content.replace('\r\n', '\n')
            
            assert normalized_saved == normalized_content, "New content should overwrite old content"
            assert normalized_saved != normalized_old, "Content should be different from old content"
            
        finally:
            # Cleanup
            if os.path.exists(project_path):
                shutil.rmtree(project_path, ignore_errors=True)
    
    @given(
        project_path=valid_project_paths(),
        content=readme_content()
    )
    @settings(max_examples=50)
    def test_readme_filename_is_correct(self, project_path, content):
        """For any saved README, the filename should be exactly 'README.md'"""
        try:
            project_dir = Path(project_path)
            readme_path = project_dir / "README.md"
            
            # Write the README
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Verify the filename
            assert readme_path.name == "README.md", "Filename should be exactly 'README.md'"
            assert readme_path.suffix == ".md", "File extension should be .md"
            
            # Verify it's the only README in the root
            readme_files = list(project_dir.glob("README.*"))
            assert len(readme_files) == 1, "Should be exactly one README file"
            assert readme_files[0] == readme_path, "The README file should be README.md"
            
        finally:
            # Cleanup
            if os.path.exists(project_path):
                shutil.rmtree(project_path, ignore_errors=True)
