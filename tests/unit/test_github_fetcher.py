"""Unit tests for GitHubFetcher."""

import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest

from app.fetchers.github_fetcher import GitHubFetcher, RepoInfo


class TestGitHubFetcher:
    """Test GitHubFetcher functionality."""
    
    def test_parse_github_url_https(self):
        """Test parsing HTTPS GitHub URLs."""
        fetcher = GitHubFetcher()
        
        result = fetcher._parse_github_url("https://github.com/owner/repo")
        assert result == ("owner", "repo")
        
        result = fetcher._parse_github_url("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")
    
    def test_parse_github_url_ssh(self):
        """Test parsing SSH GitHub URLs."""
        fetcher = GitHubFetcher()
        
        result = fetcher._parse_github_url("git@github.com:owner/repo")
        assert result == ("owner", "repo")
        
        result = fetcher._parse_github_url("git@github.com:owner/repo.git")
        assert result == ("owner", "repo")
    
    def test_parse_github_url_invalid(self):
        """Test parsing invalid URLs."""
        fetcher = GitHubFetcher()
        
        result = fetcher._parse_github_url("https://example.com/owner/repo")
        assert result is None
        
        result = fetcher._parse_github_url("not a url")
        assert result is None
    
    @patch('app.fetchers.github_fetcher.requests.Session')
    def test_extract_repo_info_success(self, mock_session_class):
        """Test successful repository info extraction."""
        # Setup mock
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'owner': {'login': 'testowner'},
            'name': 'testrepo',
            'full_name': 'testowner/testrepo',
            'description': 'Test repository',
            'default_branch': 'main',
            'stargazers_count': 42,
            'language': 'Python'
        }
        mock_session.get.return_value = mock_response
        
        fetcher = GitHubFetcher()
        fetcher.session = mock_session
        
        result = fetcher.extract_repo_info("https://github.com/testowner/testrepo")
        
        assert isinstance(result, RepoInfo)
        assert result.owner == "testowner"
        assert result.name == "testrepo"
        assert result.full_name == "testowner/testrepo"
        assert result.description == "Test repository"
        assert result.default_branch == "main"
        assert result.stars == 42
        assert result.language == "Python"
    
    @patch('app.fetchers.github_fetcher.requests.Session')
    def test_extract_repo_info_invalid_url(self, mock_session_class):
        """Test repository info extraction with invalid URL."""
        fetcher = GitHubFetcher()
        
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            fetcher.extract_repo_info("https://example.com/invalid")
    
    @patch('app.fetchers.github_fetcher.requests.Session')
    def test_extract_repo_info_rate_limit(self, mock_session_class):
        """Test handling of rate limit errors."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': str(int(os.times().elapsed) + 3600)
        }
        mock_session.get.return_value = mock_response
        
        fetcher = GitHubFetcher()
        fetcher.session = mock_session
        
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            fetcher.extract_repo_info("https://github.com/owner/repo", max_retries=1)
    
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        fetcher = GitHubFetcher()
        
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        
        assert os.path.exists(temp_dir)
        assert os.path.exists(test_file)
        
        fetcher.cleanup_temp_files(temp_dir)
        
        assert not os.path.exists(temp_dir)
    
    def test_cleanup_nonexistent_path(self):
        """Test cleanup of nonexistent path doesn't raise error."""
        fetcher = GitHubFetcher()
        
        # Should not raise an error
        fetcher.cleanup_temp_files("/nonexistent/path/12345")
    
    def test_github_token_from_env(self):
        """Test GitHub token is read from environment."""
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test_token_123'}):
            fetcher = GitHubFetcher()
            assert fetcher.github_token == 'test_token_123'
    
    def test_github_token_from_parameter(self):
        """Test GitHub token can be passed as parameter."""
        fetcher = GitHubFetcher(github_token='param_token_456')
        assert fetcher.github_token == 'param_token_456'
