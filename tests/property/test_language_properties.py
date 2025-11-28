"""
Property-based tests for language detection.
Tests Properties 5 and 6 from the design document.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile
import os
import shutil

from app.detectors import Language, ProjectType, LanguageDetector
from app.scanner import FileInfo, ProjectStructure


# Custom strategies for generating test data

@st.composite
def python_project_structure(draw):
    """
    Generate a project structure with Python configuration files.
    Returns tuple of (ProjectStructure, config_files_present)
    """
    temp_dir = tempfile.mkdtemp()
    
    # Choose which Python config files to include
    python_configs = ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile']
    num_configs = draw(st.integers(min_value=1, max_value=len(python_configs)))
    selected_configs = draw(st.lists(
        st.sampled_from(python_configs),
        min_size=num_configs,
        max_size=num_configs,
        unique=True
    ))
    
    files = []
    config_files_present = []
    
    # Create Python config files
    for config_file in selected_configs:
        filepath = os.path.join(temp_dir, config_file)
        with open(filepath, 'w') as f:
            if config_file == 'requirements.txt':
                f.write("flask==2.0.0\nrequests==2.26.0\n")
            elif config_file == 'setup.py':
                f.write("from setuptools import setup\nsetup(name='test')\n")
            elif config_file == 'pyproject.toml':
                f.write("[tool.poetry]\nname = 'test'\n")
            else:
                f.write("# Config file\n")
        
        files.append(FileInfo(
            path=config_file,
            name=config_file,
            extension='',
            size=os.path.getsize(filepath)
        ))
        config_files_present.append(config_file)
    
    # Add some Python source files
    num_py_files = draw(st.integers(min_value=0, max_value=10))
    for i in range(num_py_files):
        filename = f"module_{i}.py"
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"# Python module {i}\n")
        
        files.append(FileInfo(
            path=filename,
            name=filename,
            extension='.py',
            size=os.path.getsize(filepath)
        ))
    
    structure = ProjectStructure(
        root_path=temp_dir,
        files=files,
        directories=[],
        tree=""
    )
    
    return temp_dir, structure, config_files_present


@st.composite
def nodejs_project_structure(draw):
    """
    Generate a project structure with Node.js configuration files.
    Returns tuple of (temp_dir, ProjectStructure, config_files_present)
    """
    temp_dir = tempfile.mkdtemp()
    
    files = []
    config_files_present = []
    
    # Always include package.json for Node.js
    package_json_path = os.path.join(temp_dir, 'package.json')
    with open(package_json_path, 'w') as f:
        f.write('{"name": "test-project", "version": "1.0.0"}')
    
    files.append(FileInfo(
        path='package.json',
        name='package.json',
        extension='.json',
        size=os.path.getsize(package_json_path)
    ))
    config_files_present.append('package.json')
    
    # Add some JavaScript files
    num_js_files = draw(st.integers(min_value=0, max_value=10))
    for i in range(num_js_files):
        filename = f"module_{i}.js"
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"// JavaScript module {i}\n")
        
        files.append(FileInfo(
            path=filename,
            name=filename,
            extension='.js',
            size=os.path.getsize(filepath)
        ))
    
    structure = ProjectStructure(
        root_path=temp_dir,
        files=files,
        directories=[],
        tree=""
    )
    
    return temp_dir, structure, config_files_present


@st.composite
def rust_project_structure(draw):
    """
    Generate a project structure with Rust configuration files.
    Returns tuple of (temp_dir, ProjectStructure, config_files_present)
    """
    temp_dir = tempfile.mkdtemp()
    
    files = []
    config_files_present = []
    
    # Always include Cargo.toml for Rust
    cargo_toml_path = os.path.join(temp_dir, 'Cargo.toml')
    with open(cargo_toml_path, 'w') as f:
        f.write('[package]\nname = "test"\nversion = "0.1.0"\n')
    
    files.append(FileInfo(
        path='Cargo.toml',
        name='Cargo.toml',
        extension='.toml',
        size=os.path.getsize(cargo_toml_path)
    ))
    config_files_present.append('Cargo.toml')
    
    # Add some Rust source files
    num_rs_files = draw(st.integers(min_value=0, max_value=10))
    for i in range(num_rs_files):
        filename = f"module_{i}.rs"
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"// Rust module {i}\n")
        
        files.append(FileInfo(
            path=filename,
            name=filename,
            extension='.rs',
            size=os.path.getsize(filepath)
        ))
    
    structure = ProjectStructure(
        root_path=temp_dir,
        files=files,
        directories=[],
        tree=""
    )
    
    return temp_dir, structure, config_files_present


@st.composite
def multi_language_project_structure(draw):
    """
    Generate a project structure with multiple languages.
    Returns tuple of (temp_dir, ProjectStructure, expected_languages)
    """
    temp_dir = tempfile.mkdtemp()
    
    files = []
    expected_languages = set()
    
    # Add Python files
    num_py = draw(st.integers(min_value=1, max_value=10))
    for i in range(num_py):
        filename = f"python_{i}.py"
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"# Python {i}\n")
        files.append(FileInfo(path=filename, name=filename, extension='.py', size=os.path.getsize(filepath)))
    expected_languages.add('Python')
    
    # Add JavaScript files
    num_js = draw(st.integers(min_value=1, max_value=10))
    for i in range(num_js):
        filename = f"script_{i}.js"
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"// JavaScript {i}\n")
        files.append(FileInfo(path=filename, name=filename, extension='.js', size=os.path.getsize(filepath)))
    expected_languages.add('JavaScript')
    
    # Optionally add Rust files
    add_rust = draw(st.booleans())
    if add_rust:
        num_rs = draw(st.integers(min_value=1, max_value=5))
        for i in range(num_rs):
            filename = f"module_{i}.rs"
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"// Rust {i}\n")
            files.append(FileInfo(path=filename, name=filename, extension='.rs', size=os.path.getsize(filepath)))
        expected_languages.add('Rust')
    
    structure = ProjectStructure(
        root_path=temp_dir,
        files=files,
        directories=[],
        tree=""
    )
    
    return temp_dir, structure, expected_languages


# Property 5: Language detection from configuration files
# Feature: readme-generator, Property 5: Language detection from configuration files
# Validates: Requirements 3.1, 3.2, 3.3

class TestLanguageDetectionFromConfigFiles:
    """Test that language detector identifies languages from config files"""
    
    @given(project=python_project_structure())
    @settings(max_examples=100, deadline=None)
    def test_detects_python_from_config_files(self, project):
        """For any project with Python config files, detector should identify Python"""
        temp_dir, structure, config_files = project
        
        try:
            detector = LanguageDetector()
            
            # Test detect_python_project
            python_project = detector.detect_python_project(structure.files)
            
            assert python_project is not None, \
                "Should detect Python project when config files present"
            assert python_project.language == 'Python', \
                f"Language should be Python, got {python_project.language}"
            
            # Verify config files are recorded
            for config_file in config_files:
                assert config_file in python_project.config_files, \
                    f"Config file {config_file} should be recorded"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(project=nodejs_project_structure())
    @settings(max_examples=100, deadline=None)
    def test_detects_nodejs_from_package_json(self, project):
        """For any project with package.json, detector should identify Node.js"""
        temp_dir, structure, config_files = project
        
        try:
            detector = LanguageDetector()
            
            # Test detect_nodejs_project
            nodejs_project = detector.detect_nodejs_project(structure.files)
            
            assert nodejs_project is not None, \
                "Should detect Node.js project when package.json present"
            assert nodejs_project.language == 'Node.js', \
                f"Language should be Node.js, got {nodejs_project.language}"
            
            # Verify package.json is recorded
            assert 'package.json' in nodejs_project.config_files, \
                "package.json should be recorded in config files"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(project=rust_project_structure())
    @settings(max_examples=100, deadline=None)
    def test_detects_rust_from_cargo_toml(self, project):
        """For any project with Cargo.toml, detector should identify Rust"""
        temp_dir, structure, config_files = project
        
        try:
            detector = LanguageDetector()
            
            # Test detect_rust_project
            rust_project = detector.detect_rust_project(structure.files)
            
            assert rust_project is not None, \
                "Should detect Rust project when Cargo.toml present"
            assert rust_project.language == 'Rust', \
                f"Language should be Rust, got {rust_project.language}"
            
            # Verify Cargo.toml is recorded
            assert 'Cargo.toml' in rust_project.config_files, \
                "Cargo.toml should be recorded in config files"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        has_requirements=st.booleans(),
        has_setup_py=st.booleans(),
        has_pyproject=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    def test_python_detection_with_various_config_combinations(
        self, has_requirements, has_setup_py, has_pyproject
    ):
        """For any combination of Python config files, detection should work correctly"""
        # Skip if no config files
        assume(has_requirements or has_setup_py or has_pyproject)
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            files = []
            expected_configs = []
            
            if has_requirements:
                filepath = os.path.join(temp_dir, 'requirements.txt')
                with open(filepath, 'w') as f:
                    f.write("flask==2.0.0\n")
                files.append(FileInfo(
                    path='requirements.txt',
                    name='requirements.txt',
                    extension='.txt',
                    size=os.path.getsize(filepath)
                ))
                expected_configs.append('requirements.txt')
            
            if has_setup_py:
                filepath = os.path.join(temp_dir, 'setup.py')
                with open(filepath, 'w') as f:
                    f.write("from setuptools import setup\n")
                files.append(FileInfo(
                    path='setup.py',
                    name='setup.py',
                    extension='.py',
                    size=os.path.getsize(filepath)
                ))
                expected_configs.append('setup.py')
            
            if has_pyproject:
                filepath = os.path.join(temp_dir, 'pyproject.toml')
                with open(filepath, 'w') as f:
                    f.write("[tool.poetry]\n")
                files.append(FileInfo(
                    path='pyproject.toml',
                    name='pyproject.toml',
                    extension='.toml',
                    size=os.path.getsize(filepath)
                ))
                expected_configs.append('pyproject.toml')
            
            detector = LanguageDetector()
            python_project = detector.detect_python_project(files)
            
            assert python_project is not None, \
                "Should detect Python project with any config file"
            assert python_project.language == 'Python'
            
            # All expected configs should be found
            for config in expected_configs:
                assert config in python_project.config_files, \
                    f"Config {config} should be detected"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 6: Multi-language detection
# Feature: readme-generator, Property 6: Multi-language detection
# Validates: Requirements 3.4

class TestMultiLanguageDetection:
    """Test that language detector identifies all languages and determines primary"""
    
    @given(project=multi_language_project_structure())
    @settings(max_examples=100, deadline=None)
    def test_detects_all_present_languages(self, project):
        """For any project with multiple languages, detector should identify all"""
        temp_dir, structure, expected_languages = project
        
        try:
            detector = LanguageDetector()
            
            # Detect all languages
            detected_languages = detector.detect_languages(structure)
            
            # Should detect at least as many languages as we created
            detected_language_names = {lang.name for lang in detected_languages}
            
            assert len(detected_language_names) >= len(expected_languages), \
                f"Should detect at least {len(expected_languages)} languages"
            
            # All expected languages should be detected
            for expected_lang in expected_languages:
                assert expected_lang in detected_language_names, \
                    f"Language {expected_lang} should be detected"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(project=multi_language_project_structure())
    @settings(max_examples=100, deadline=None)
    def test_determines_primary_language(self, project):
        """For any multi-language project, detector should determine a primary language"""
        temp_dir, structure, expected_languages = project
        
        try:
            detector = LanguageDetector()
            
            # Detect all languages
            detected_languages = detector.detect_languages(structure)
            
            # Get primary language
            primary = detector.get_primary_language(detected_languages)
            
            assert primary is not None, \
                "Should determine a primary language"
            assert primary.name in expected_languages, \
                f"Primary language {primary.name} should be one of the detected languages"
            
            # Primary should have highest confidence
            if len(detected_languages) > 1:
                for lang in detected_languages[1:]:
                    assert primary.confidence >= lang.confidence, \
                        "Primary language should have highest confidence"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        num_py_files=st.integers(min_value=1, max_value=20),
        num_js_files=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    def test_primary_language_based_on_file_count(self, num_py_files, num_js_files):
        """For any project, primary language should be determined by file count"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            files = []
            
            # Create Python files
            for i in range(num_py_files):
                filename = f"python_{i}.py"
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(f"# Python {i}\n")
                files.append(FileInfo(
                    path=filename,
                    name=filename,
                    extension='.py',
                    size=os.path.getsize(filepath)
                ))
            
            # Create JavaScript files
            for i in range(num_js_files):
                filename = f"script_{i}.js"
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(f"// JavaScript {i}\n")
                files.append(FileInfo(
                    path=filename,
                    name=filename,
                    extension='.js',
                    size=os.path.getsize(filepath)
                ))
            
            structure = ProjectStructure(
                root_path=temp_dir,
                files=files,
                directories=[],
                tree=""
            )
            
            detector = LanguageDetector()
            detected_languages = detector.detect_languages(structure)
            primary = detector.get_primary_language(detected_languages)
            
            # Primary should be the language with more files
            if num_py_files > num_js_files:
                assert primary.name == 'Python', \
                    f"Primary should be Python with {num_py_files} files vs {num_js_files} JS files"
            elif num_js_files > num_py_files:
                assert primary.name == 'JavaScript', \
                    f"Primary should be JavaScript with {num_js_files} files vs {num_py_files} Python files"
            else:
                # Equal counts - either is acceptable
                assert primary.name in ['Python', 'JavaScript']
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(num_files=st.integers(min_value=1, max_value=50))
    @settings(max_examples=100, deadline=None)
    def test_confidence_scores_sum_to_one(self, num_files):
        """For any project, confidence scores should sum to approximately 1.0"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            files = []
            
            # Create random mix of Python and JavaScript files
            for i in range(num_files):
                if i % 2 == 0:
                    filename = f"file_{i}.py"
                    ext = '.py'
                else:
                    filename = f"file_{i}.js"
                    ext = '.js'
                
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(f"// File {i}\n")
                
                files.append(FileInfo(
                    path=filename,
                    name=filename,
                    extension=ext,
                    size=os.path.getsize(filepath)
                ))
            
            structure = ProjectStructure(
                root_path=temp_dir,
                files=files,
                directories=[],
                tree=""
            )
            
            detector = LanguageDetector()
            detected_languages = detector.detect_languages(structure)
            
            # Sum of confidence scores should be approximately 1.0
            total_confidence = sum(lang.confidence for lang in detected_languages)
            
            assert abs(total_confidence - 1.0) < 0.01, \
                f"Confidence scores should sum to ~1.0, got {total_confidence}"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(structure=multi_language_project_structure())
    @settings(max_examples=100, deadline=None)
    def test_each_language_has_indicators(self, structure):
        """For any detected language, it should have indicator files listed"""
        temp_dir, project_structure, expected_languages = structure
        
        try:
            detector = LanguageDetector()
            detected_languages = detector.detect_languages(project_structure)
            
            # Every detected language should have indicators
            for lang in detected_languages:
                assert len(lang.indicators) > 0, \
                    f"Language {lang.name} should have indicator files"
                
                # All indicators should be valid file paths from the project
                project_file_paths = {f.path for f in project_structure.files}
                for indicator in lang.indicators:
                    assert indicator in project_file_paths, \
                        f"Indicator {indicator} should be a valid project file"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
