"""
Property-based tests for dependency extraction.
Tests Properties 7 and 8 from the design document.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile
import os
import json
import shutil

from app.extractors import DependencyExtractor, Dependency, Dependencies
from app.detectors import ProjectType


# Custom strategies for generating test data

@st.composite
def python_package_names(draw):
    """Generate valid Python package names"""
    # Python package names: ASCII letters, numbers, hyphens, underscores
    # Must start with a letter
    first_char = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz'))
    rest = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_',
        min_size=0,
        max_size=49
    ))
    
    return first_char + rest


@st.composite
def version_strings(draw):
    """Generate valid version strings"""
    major = draw(st.integers(min_value=0, max_value=99))
    minor = draw(st.integers(min_value=0, max_value=99))
    patch = draw(st.integers(min_value=0, max_value=99))
    
    return f"{major}.{minor}.{patch}"


@st.composite
def python_requirements_content(draw):
    """Generate valid requirements.txt content"""
    num_packages = draw(st.integers(min_value=1, max_value=20))
    
    lines = []
    packages = []
    seen_names = set()
    
    for _ in range(num_packages):
        package_name = draw(python_package_names())
        
        # Skip if we've already seen this package name
        if package_name in seen_names:
            continue
        
        seen_names.add(package_name)
        
        # Sometimes include version, sometimes not
        include_version = draw(st.booleans())
        
        if include_version:
            version = draw(version_strings())
            operator = draw(st.sampled_from(['==', '>=', '<=', '>', '<', '~=']))
            line = f"{package_name}{operator}{version}"
            packages.append((package_name, version))
        else:
            line = package_name
            packages.append((package_name, None))
        
        lines.append(line)
    
    # Add some comments and empty lines
    if draw(st.booleans()):
        lines.insert(0, "# This is a comment")
    
    if draw(st.booleans()):
        lines.append("")
    
    return '\n'.join(lines), packages


@st.composite
def nodejs_package_names(draw):
    """Generate valid Node.js package names"""
    # Can have scope like @scope/package
    has_scope = draw(st.booleans())
    
    if has_scope:
        scope = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=20
        ).filter(lambda x: x and x[0].isalnum()))
        
        package = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda x: x and x[0].isalnum()))
        
        return f"@{scope}/{package}"
    else:
        return draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda x: x and x[0].isalnum()))


@st.composite
def package_json_content(draw):
    """Generate valid package.json content"""
    num_deps = draw(st.integers(min_value=0, max_value=15))
    num_dev_deps = draw(st.integers(min_value=0, max_value=15))
    
    dependencies = {}
    dev_dependencies = {}
    
    for _ in range(num_deps):
        package_name = draw(nodejs_package_names())
        version = draw(st.sampled_from([
            f"^{draw(version_strings())}",
            f"~{draw(version_strings())}",
            f"{draw(version_strings())}",
            f">={draw(version_strings())}",
        ]))
        dependencies[package_name] = version
    
    for _ in range(num_dev_deps):
        package_name = draw(nodejs_package_names())
        version = draw(st.sampled_from([
            f"^{draw(version_strings())}",
            f"~{draw(version_strings())}",
            f"{draw(version_strings())}",
        ]))
        dev_dependencies[package_name] = version
    
    package_data = {
        "name": draw(nodejs_package_names()),
        "version": draw(version_strings()),
        "dependencies": dependencies,
        "devDependencies": dev_dependencies
    }
    
    return json.dumps(package_data, indent=2), dependencies, dev_dependencies


@st.composite
def cargo_toml_content(draw):
    """Generate valid Cargo.toml content"""
    num_deps = draw(st.integers(min_value=1, max_value=15))
    num_dev_deps = draw(st.integers(min_value=0, max_value=10))
    
    lines = ['[package]']
    lines.append(f'name = "test-project"')
    lines.append(f'version = "{draw(version_strings())}"')
    lines.append('')
    lines.append('[dependencies]')
    
    dependencies = []
    seen_names = set()
    
    for _ in range(num_deps):
        # Rust package names: ASCII letters, numbers, hyphens, underscores
        first_char = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz'))
        rest = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_',
            min_size=0,
            max_size=29
        ))
        package_name = first_char + rest
        
        # Skip if we've already seen this package name
        if package_name in seen_names:
            continue
        
        seen_names.add(package_name)
        
        version = draw(version_strings())
        lines.append(f'{package_name} = "{version}"')
        dependencies.append((package_name, version))
    
    if num_dev_deps > 0:
        lines.append('')
        lines.append('[dev-dependencies]')
        
        for _ in range(num_dev_deps):
            first_char = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz'))
            rest = draw(st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_',
                min_size=0,
                max_size=29
            ))
            package_name = first_char + rest
            
            # Skip if we've already seen this package name
            if package_name in seen_names:
                continue
            
            seen_names.add(package_name)
            
            version = draw(version_strings())
            lines.append(f'{package_name} = "{version}"')
    
    return '\n'.join(lines), dependencies


# Property 7: Dependency extraction correctness
# Feature: readme-generator, Property 7: Dependency extraction correctness
# Validates: Requirements 4.1, 4.2, 4.3

class TestDependencyExtractionCorrectness:
    """Test that dependencies are correctly extracted from configuration files"""
    
    @given(content_data=python_requirements_content())
    @settings(max_examples=100)
    def test_python_requirements_extraction(self, content_data):
        """For any valid requirements.txt, all dependencies should be extracted"""
        content, expected_packages = content_data
        
        # Create temporary directory and file
        temp_dir = tempfile.mkdtemp()
        requirements_file = Path(temp_dir) / 'requirements.txt'
        
        try:
            requirements_file.write_text(content)
            
            # Create project type
            project_type = ProjectType(
                language='Python',
                framework=None,
                config_files=['requirements.txt']
            )
            
            # Extract dependencies
            extractor = DependencyExtractor()
            dependencies = extractor.extract_dependencies(project_type, temp_dir)
            
            # Verify all packages are extracted
            extracted_names = {dep.name for dep in dependencies.runtime}
            expected_names = {pkg[0] for pkg in expected_packages}
            
            assert extracted_names == expected_names, \
                f"Expected packages {expected_names}, got {extracted_names}"
            
            # Verify versions are extracted correctly
            for dep in dependencies.runtime:
                matching_packages = [pkg for pkg in expected_packages if pkg[0] == dep.name]
                if matching_packages:
                    expected_version = matching_packages[0][1]
                    if expected_version:
                        assert dep.version is not None, \
                            f"Package {dep.name} should have version {expected_version}"
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(content_data=package_json_content())
    @settings(max_examples=100)
    def test_nodejs_package_json_extraction(self, content_data):
        """For any valid package.json, all dependencies should be extracted"""
        content, expected_deps, expected_dev_deps = content_data
        
        # Create temporary directory and file
        temp_dir = tempfile.mkdtemp()
        package_file = Path(temp_dir) / 'package.json'
        
        try:
            package_file.write_text(content)
            
            # Create project type
            project_type = ProjectType(
                language='Node.js',
                framework=None,
                config_files=['package.json']
            )
            
            # Extract dependencies
            extractor = DependencyExtractor()
            dependencies = extractor.extract_dependencies(project_type, temp_dir)
            
            # Verify runtime dependencies
            extracted_runtime_names = {dep.name for dep in dependencies.runtime}
            expected_runtime_names = set(expected_deps.keys())
            
            assert extracted_runtime_names == expected_runtime_names, \
                f"Expected runtime deps {expected_runtime_names}, got {extracted_runtime_names}"
            
            # Verify dev dependencies
            extracted_dev_names = {dep.name for dep in dependencies.development}
            expected_dev_names = set(expected_dev_deps.keys())
            
            assert extracted_dev_names == expected_dev_names, \
                f"Expected dev deps {expected_dev_names}, got {extracted_dev_names}"
            
            # Verify versions are extracted
            for dep in dependencies.runtime:
                assert dep.version is not None, f"Runtime dependency {dep.name} should have version"
            
            for dep in dependencies.development:
                assert dep.version is not None, f"Dev dependency {dep.name} should have version"
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(content_data=cargo_toml_content())
    @settings(max_examples=100)
    def test_rust_cargo_toml_extraction(self, content_data):
        """For any valid Cargo.toml, all dependencies should be extracted"""
        content, expected_deps = content_data
        
        # Create temporary directory and file
        temp_dir = tempfile.mkdtemp()
        cargo_file = Path(temp_dir) / 'Cargo.toml'
        
        try:
            cargo_file.write_text(content)
            
            # Create project type
            project_type = ProjectType(
                language='Rust',
                framework=None,
                config_files=['Cargo.toml']
            )
            
            # Extract dependencies
            extractor = DependencyExtractor()
            dependencies = extractor.extract_dependencies(project_type, temp_dir)
            
            # Verify all packages are extracted
            extracted_names = {dep.name for dep in dependencies.runtime}
            expected_names = {pkg[0] for pkg in expected_deps}
            
            assert extracted_names == expected_names, \
                f"Expected packages {expected_names}, got {extracted_names}"
            
            # Verify versions are extracted
            for dep in dependencies.runtime:
                assert dep.version is not None, f"Dependency {dep.name} should have version"
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# Property 8: Structured dependency output
# Feature: readme-generator, Property 8: Structured dependency output
# Validates: Requirements 4.5

class TestStructuredDependencyOutput:
    """Test that extracted dependencies are properly structured"""
    
    @given(content_data=python_requirements_content())
    @settings(max_examples=100)
    def test_python_dependencies_structure(self, content_data):
        """For any extracted Python dependencies, output should be structured correctly"""
        content, expected_packages = content_data
        
        # Create temporary directory and file
        temp_dir = tempfile.mkdtemp()
        requirements_file = Path(temp_dir) / 'requirements.txt'
        
        try:
            requirements_file.write_text(content)
            
            project_type = ProjectType(
                language='Python',
                framework=None,
                config_files=['requirements.txt']
            )
            
            extractor = DependencyExtractor()
            dependencies = extractor.extract_dependencies(project_type, temp_dir)
            
            # Verify structure
            assert isinstance(dependencies, Dependencies), \
                "Output should be Dependencies object"
            
            assert isinstance(dependencies.runtime, list), \
                "Runtime dependencies should be a list"
            
            assert isinstance(dependencies.development, list), \
                "Development dependencies should be a list"
            
            # Verify each dependency has correct structure
            for dep in dependencies.runtime:
                assert isinstance(dep, Dependency), \
                    "Each dependency should be a Dependency object"
                assert isinstance(dep.name, str), \
                    "Dependency name should be a string"
                assert dep.name, "Dependency name should not be empty"
                assert isinstance(dep.dev, bool), \
                    "Dependency dev flag should be boolean"
                assert dep.dev is False, \
                    "Runtime dependencies should have dev=False"
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(content_data=package_json_content())
    @settings(max_examples=100)
    def test_nodejs_dependencies_structure(self, content_data):
        """For any extracted Node.js dependencies, output should be structured correctly"""
        content, expected_deps, expected_dev_deps = content_data
        
        # Create temporary directory and file
        temp_dir = tempfile.mkdtemp()
        package_file = Path(temp_dir) / 'package.json'
        
        try:
            package_file.write_text(content)
            
            project_type = ProjectType(
                language='Node.js',
                framework=None,
                config_files=['package.json']
            )
            
            extractor = DependencyExtractor()
            dependencies = extractor.extract_dependencies(project_type, temp_dir)
            
            # Verify structure
            assert isinstance(dependencies, Dependencies), \
                "Output should be Dependencies object"
            
            # Verify runtime dependencies structure
            for dep in dependencies.runtime:
                assert isinstance(dep, Dependency), \
                    "Each dependency should be a Dependency object"
                assert isinstance(dep.name, str) and dep.name, \
                    "Dependency name should be non-empty string"
                assert dep.dev is False, \
                    "Runtime dependencies should have dev=False"
            
            # Verify development dependencies structure
            for dep in dependencies.development:
                assert isinstance(dep, Dependency), \
                    "Each dev dependency should be a Dependency object"
                assert isinstance(dep.name, str) and dep.name, \
                    "Dev dependency name should be non-empty string"
                assert dep.dev is True, \
                    "Development dependencies should have dev=True"
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        language=st.sampled_from(['Python', 'Node.js', 'Rust']),
        config_file=st.sampled_from(['requirements.txt', 'package.json', 'Cargo.toml'])
    )
    @settings(max_examples=50)
    def test_empty_or_missing_files_return_empty_structure(self, language, config_file):
        """For any missing or empty config file, should return empty but valid structure"""
        # Create temporary directory without config file
        temp_dir = tempfile.mkdtemp()
        
        try:
            project_type = ProjectType(
                language=language,
                framework=None,
                config_files=[config_file]
            )
            
            extractor = DependencyExtractor()
            dependencies = extractor.extract_dependencies(project_type, temp_dir)
            
            # Should return valid structure even if empty
            assert isinstance(dependencies, Dependencies), \
                "Should return Dependencies object even for missing files"
            assert isinstance(dependencies.runtime, list), \
                "Runtime should be a list"
            assert isinstance(dependencies.development, list), \
                "Development should be a list"
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
