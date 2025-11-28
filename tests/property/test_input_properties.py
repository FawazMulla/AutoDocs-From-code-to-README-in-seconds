"""
Property-based tests for input validation.
Tests Properties 1 and 2 from the design document.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile
import os
import shutil

from app.validators import InputValidator, ValidationResult


# Custom strategies for generating test data

@st.composite
def valid_local_paths(draw):
    """Generate valid local paths that exist on the filesystem"""
    # Create a temporary directory that we know exists
    temp_dir = tempfile.mkdtemp()
    # Register cleanup (will be handled by test teardown)
    return temp_dir


@st.composite
def invalid_local_paths(draw):
    """Generate invalid local paths"""
    # Generate various types of invalid paths
    invalid_type = draw(st.sampled_from([
        'nonexistent',
        'file_not_dir',
        'empty',
        'null_bytes',
    ]))
    
    if invalid_type == 'nonexistent':
        # Generate a path that doesn't exist
        random_name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=10,
            max_size=50
        ))
        return f"/nonexistent/path/{random_name}"
    
    elif invalid_type == 'file_not_dir':
        # Create a temporary file (not a directory)
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        return temp_file.name
    
    elif invalid_type == 'empty':
        return ""
    
    elif invalid_type == 'null_bytes':
        base_path = draw(st.text(min_size=1, max_size=20))
        return base_path + '\0' + 'injection'


@st.composite
def valid_github_urls(draw):
    """Generate valid GitHub repository URLs"""
    username = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-'),
        min_size=1,
        max_size=39  # GitHub username max length
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    repo_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='.-_'),
        min_size=1,
        max_size=100
    ).filter(lambda x: x and x[0] not in '.-'))
    
    url_format = draw(st.sampled_from([
        f"https://github.com/{username}/{repo_name}",
        f"https://github.com/{username}/{repo_name}/",
        f"https://github.com/{username}/{repo_name}.git",
        f"http://github.com/{username}/{repo_name}",
        f"git@github.com:{username}/{repo_name}.git",
    ]))
    
    return url_format


@st.composite
def invalid_github_urls(draw):
    """Generate invalid GitHub URLs"""
    invalid_type = draw(st.sampled_from([
        'wrong_domain',
        'missing_parts',
        'invalid_chars',
        'empty',
        'malformed'
    ]))
    
    if invalid_type == 'wrong_domain':
        return draw(st.sampled_from([
            "https://gitlab.com/user/repo",
            "https://bitbucket.org/user/repo",
            "https://example.com/user/repo"
        ]))
    
    elif invalid_type == 'missing_parts':
        return draw(st.sampled_from([
            "https://github.com/",
            "https://github.com/user",
            "https://github.com/user/",
        ]))
    
    elif invalid_type == 'invalid_chars':
        return "https://github.com/user name/repo name"
    
    elif invalid_type == 'empty':
        return ""
    
    elif invalid_type == 'malformed':
        return draw(st.sampled_from([
            "not a url at all",
            "github.com/user/repo",  # missing protocol
            "https://github/user/repo",  # missing .com
            "https://github.com/user/repo/extra/path",  # too many parts
        ]))


# Property 1: Valid input acceptance
# Feature: readme-generator, Property 1: Valid input acceptance
# Validates: Requirements 1.1, 1.2

class TestValidInputAcceptance:
    """Test that valid inputs are accepted"""
    
    @given(path=valid_local_paths())
    @settings(max_examples=100)
    def test_valid_local_paths_are_accepted(self, path):
        """For any valid local path, the validator should accept it"""
        validator = InputValidator()
        result = validator.validate_local_path(path)
        
        # Cleanup
        if os.path.exists(path) and path.startswith(tempfile.gettempdir()):
            shutil.rmtree(path, ignore_errors=True)
        
        assert result.valid is True, f"Valid path {path} should be accepted"
        assert result.error_message is None, "Valid path should not have error message"
        assert result.sanitized_input is not None, "Valid path should have sanitized input"
    
    @given(url=valid_github_urls())
    @settings(max_examples=100)
    def test_valid_github_urls_are_accepted(self, url):
        """For any valid GitHub URL, the validator should accept it"""
        validator = InputValidator()
        result = validator.validate_github_url(url)
        
        assert result.valid is True, f"Valid GitHub URL {url} should be accepted"
        assert result.error_message is None, "Valid URL should not have error message"
        assert result.sanitized_input is not None, "Valid URL should have sanitized input"


# Property 2: Invalid input rejection
# Feature: readme-generator, Property 2: Invalid input rejection
# Validates: Requirements 1.3

class TestInvalidInputRejection:
    """Test that invalid inputs are rejected"""
    
    @given(path=invalid_local_paths())
    @settings(max_examples=100)
    def test_invalid_local_paths_are_rejected(self, path):
        """For any invalid local path, the validator should reject it"""
        validator = InputValidator()
        result = validator.validate_local_path(path)
        
        # Cleanup temporary files if created
        if path and os.path.exists(path) and os.path.isfile(path):
            try:
                os.unlink(path)
            except:
                pass
        
        assert result.valid is False, f"Invalid path {path} should be rejected"
        assert result.error_message is not None, "Invalid path should have error message"
    
    @given(url=invalid_github_urls())
    @settings(max_examples=100)
    def test_invalid_github_urls_are_rejected(self, url):
        """For any invalid GitHub URL, the validator should reject it"""
        validator = InputValidator()
        result = validator.validate_github_url(url)
        
        assert result.valid is False, f"Invalid GitHub URL {url} should be rejected"
        assert result.error_message is not None, "Invalid URL should have error message"
    
    @given(input_val=st.one_of(st.none(), st.integers(), st.lists(st.text())))
    @settings(max_examples=50)
    def test_non_string_inputs_are_rejected(self, input_val):
        """For any non-string input, the validator should reject it"""
        validator = InputValidator()
        
        # Test with local path validation
        result = validator.validate_local_path(input_val)
        assert result.valid is False, f"Non-string input {type(input_val)} should be rejected"
        
        # Test with GitHub URL validation
        result = validator.validate_github_url(input_val)
        assert result.valid is False, f"Non-string input {type(input_val)} should be rejected"
