"""
Property-based tests for project scanner.
Tests Properties 3 and 4 from the design document.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile
import os
import shutil

from app.scanner import ProjectScanner, FileInfo, ProjectStructure


# Custom strategies for generating test data

@st.composite
def directory_structures(draw):
    """
    Generate temporary directory structures with random files and subdirectories.
    Returns tuple of (temp_dir_path, expected_file_count, expected_dir_count)
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Generate random number of files and directories
    num_files = draw(st.integers(min_value=0, max_value=20))
    num_dirs = draw(st.integers(min_value=0, max_value=10))
    
    created_files = 0
    created_dirs = 0
    
    # Create files in root
    for i in range(num_files):
        filename = f"file_{i}.txt"
        filepath = os.path.join(temp_dir, filename)
        try:
            with open(filepath, 'w') as f:
                f.write(f"Content {i}")
            created_files += 1
        except:
            pass
    
    # Create subdirectories with files
    for i in range(num_dirs):
        dirname = f"dir_{i}"
        dirpath = os.path.join(temp_dir, dirname)
        try:
            os.makedirs(dirpath, exist_ok=True)
            created_dirs += 1
            
            # Add some files to subdirectory
            subfiles = draw(st.integers(min_value=0, max_value=5))
            for j in range(subfiles):
                subfile = os.path.join(dirpath, f"subfile_{j}.py")
                try:
                    with open(subfile, 'w') as f:
                        f.write(f"# Python file {j}")
                    created_files += 1
                except:
                    pass
        except:
            pass
    
    return temp_dir, created_files, created_dirs


@st.composite
def nested_directory_structures(draw):
    """
    Generate deeply nested directory structures.
    Returns tuple of (temp_dir_path, all_files, all_dirs)
    """
    temp_dir = tempfile.mkdtemp()
    
    # Generate nested structure
    depth = draw(st.integers(min_value=1, max_value=5))
    
    all_files = []
    all_dirs = []
    
    current_path = temp_dir
    
    # Create nested directories
    for level in range(depth):
        dirname = f"level_{level}"
        current_path = os.path.join(current_path, dirname)
        try:
            os.makedirs(current_path, exist_ok=True)
            all_dirs.append(current_path)
            
            # Add a file at this level
            filename = f"file_at_level_{level}.txt"
            filepath = os.path.join(current_path, filename)
            with open(filepath, 'w') as f:
                f.write(f"Level {level}")
            all_files.append(filepath)
        except:
            pass
    
    return temp_dir, all_files, all_dirs


# Property 3: Complete directory traversal
# Feature: readme-generator, Property 3: Complete directory traversal
# Validates: Requirements 2.1, 2.2, 2.3

class TestCompleteDirectoryTraversal:
    """Test that scanner discovers all files and directories"""
    
    @given(structure=directory_structures())
    @settings(max_examples=100, deadline=None)
    def test_scanner_discovers_all_files(self, structure):
        """For any directory structure, scanner should discover all files"""
        temp_dir, expected_files, expected_dirs = structure
        
        try:
            scanner = ProjectScanner()
            result = scanner.scan_directory(temp_dir)
            
            # Count actual files and directories
            actual_files = len(result.files)
            actual_dirs = len(result.directories)
            
            # Scanner should find all files
            assert actual_files == expected_files, \
                f"Expected {expected_files} files, found {actual_files}"
            
            # Scanner should find all directories
            assert actual_dirs == expected_dirs, \
                f"Expected {expected_dirs} directories, found {actual_dirs}"
            
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(structure=nested_directory_structures())
    @settings(max_examples=100, deadline=None)
    def test_scanner_traverses_nested_directories(self, structure):
        """For any nested directory structure, scanner should traverse all levels"""
        temp_dir, expected_files, expected_dirs = structure
        
        try:
            scanner = ProjectScanner()
            result = scanner.scan_directory(temp_dir)
            
            # All created files should be discovered
            discovered_file_paths = [
                os.path.join(result.root_path, f.path) 
                for f in result.files
            ]
            
            for expected_file in expected_files:
                assert expected_file in discovered_file_paths, \
                    f"File {expected_file} should be discovered"
            
            # All created directories should be discovered
            discovered_dir_paths = [
                os.path.join(result.root_path, d) 
                for d in result.directories
            ]
            
            for expected_dir in expected_dirs:
                assert expected_dir in discovered_dir_paths, \
                    f"Directory {expected_dir} should be discovered"
            
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        num_files=st.integers(min_value=1, max_value=50),
        num_dirs=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    def test_scanner_count_matches_filesystem(self, num_files, num_dirs):
        """For any directory, discovered count should match actual filesystem count"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create known structure
            actual_files = 0
            actual_dirs = 0
            
            # Create files
            for i in range(num_files):
                filepath = os.path.join(temp_dir, f"file_{i}.txt")
                with open(filepath, 'w') as f:
                    f.write(f"Content {i}")
                actual_files += 1
            
            # Create directories
            for i in range(num_dirs):
                dirpath = os.path.join(temp_dir, f"dir_{i}")
                os.makedirs(dirpath, exist_ok=True)
                actual_dirs += 1
            
            # Scan
            scanner = ProjectScanner()
            result = scanner.scan_directory(temp_dir)
            
            # Verify counts match
            assert len(result.files) == actual_files, \
                f"File count mismatch: expected {actual_files}, got {len(result.files)}"
            assert len(result.directories) == actual_dirs, \
                f"Directory count mismatch: expected {actual_dirs}, got {len(result.directories)}"
            
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 4: File information completeness
# Feature: readme-generator, Property 4: File information completeness
# Validates: Requirements 2.2

class TestFileInformationCompleteness:
    """Test that scanner records complete file information"""
    
    @given(
        filename=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x and x[0] not in '-'),
        extension=st.sampled_from(['.txt', '.py', '.js', '.md', '.json', '.toml', ''])
    )
    @settings(max_examples=100, deadline=None)
    def test_scanner_records_file_path_name_extension(self, filename, extension):
        """For any scanned file, scanner should record path, name, and extension"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create a file with specific name and extension
            full_filename = filename + extension
            filepath = os.path.join(temp_dir, full_filename)
            
            with open(filepath, 'w') as f:
                f.write("Test content")
            
            # Scan
            scanner = ProjectScanner()
            result = scanner.scan_directory(temp_dir)
            
            # Should find exactly one file
            assert len(result.files) == 1, "Should find exactly one file"
            
            file_info = result.files[0]
            
            # Verify all fields are populated
            assert file_info.path is not None, "Path should be recorded"
            assert file_info.name is not None, "Name should be recorded"
            assert file_info.extension is not None, "Extension should be recorded"
            assert file_info.size >= 0, "Size should be recorded"
            
            # Verify correctness
            assert file_info.name == full_filename, \
                f"Name should be {full_filename}, got {file_info.name}"
            assert file_info.extension == extension, \
                f"Extension should be {extension}, got {file_info.extension}"
            
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(content=st.text(min_size=0, max_size=1000))
    @settings(max_examples=100, deadline=None)
    def test_scanner_records_correct_file_size(self, content):
        """For any file, scanner should record correct size"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create a file with specific content
            filepath = os.path.join(temp_dir, "test_file.txt")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Get actual size
            actual_size = os.path.getsize(filepath)
            
            # Scan
            scanner = ProjectScanner()
            result = scanner.scan_directory(temp_dir)
            
            # Should find exactly one file
            assert len(result.files) == 1, "Should find exactly one file"
            
            file_info = result.files[0]
            
            # Verify size matches
            assert file_info.size == actual_size, \
                f"Size should be {actual_size}, got {file_info.size}"
            
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(structure=directory_structures())
    @settings(max_examples=100, deadline=None)
    def test_all_files_have_complete_information(self, structure):
        """For any directory structure, all discovered files should have complete info"""
        temp_dir, _, _ = structure
        
        try:
            scanner = ProjectScanner()
            result = scanner.scan_directory(temp_dir)
            
            # Every file should have complete information
            for file_info in result.files:
                assert file_info.path, "Every file should have a path"
                assert file_info.name, "Every file should have a name"
                assert file_info.extension is not None, "Every file should have extension field"
                assert file_info.size >= 0, "Every file should have non-negative size"
                
                # Path should end with name
                assert file_info.path.endswith(file_info.name), \
                    f"Path {file_info.path} should end with name {file_info.name}"
            
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
