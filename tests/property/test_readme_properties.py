"""
Property-based tests for README generation.
Tests Properties 9, 10, 11, 12, 13, 24, 25, 26 from the design document.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile
import os
import shutil
import re

from app.builders import READMEBuilder, BuildContext
from app.detectors import ProjectType, Language
from app.scanner import FileInfo, ProjectStructure
from app.extractors import Dependencies, Dependency, Scripts, Script
from app.templates import TemplateEngine


# Custom strategies for generating test data

@st.composite
def language_strategy(draw):
    """Generate a random Language."""
    languages = ['Python', 'JavaScript', 'TypeScript', 'Rust', 'Go', 'Java', 'C++']
    name = draw(st.sampled_from(languages))
    confidence = draw(st.floats(min_value=0.1, max_value=1.0))
    indicators = draw(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5))
    
    return Language(name=name, confidence=confidence, indicators=indicators)


@st.composite
def project_type_strategy(draw):
    """Generate a random ProjectType."""
    languages = ['Python', 'Node.js', 'Rust', 'Go', 'Java']
    frameworks = [None, 'Django', 'Flask', 'React', 'Express', 'Vue', 'Angular']
    
    language = draw(st.sampled_from(languages))
    framework = draw(st.sampled_from(frameworks))
    
    return ProjectType(
        language=language,
        framework=framework,
        config_files=[]
    )


@st.composite
def dependency_strategy(draw):
    """Generate a random Dependency."""
    name = draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_')))
    version = draw(st.one_of(st.none(), st.text(min_size=1, max_size=10)))
    dev = draw(st.booleans())
    
    return Dependency(name=name, version=version, dev=dev)


@st.composite
def dependencies_strategy(draw):
    """Generate random Dependencies."""
    runtime = draw(st.lists(dependency_strategy(), min_size=0, max_size=10))
    development = draw(st.lists(dependency_strategy(), min_size=0, max_size=10))
    
    return Dependencies(runtime=runtime, development=development)


@st.composite
def script_strategy(draw):
    """Generate a random Script."""
    name = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_')))
    command = draw(st.text(min_size=1, max_size=50))
    description = draw(st.one_of(st.none(), st.text(min_size=1, max_size=100)))
    
    return Script(name=name, command=command, description=description)


@st.composite
def scripts_strategy(draw):
    """Generate random Scripts."""
    items = draw(st.lists(script_strategy(), min_size=0, max_size=10))
    
    return Scripts(items=items)


@st.composite
def project_structure_strategy(draw):
    """Generate a random ProjectStructure."""
    temp_dir = tempfile.mkdtemp()
    
    # Generate files
    num_files = draw(st.integers(min_value=1, max_value=20))
    files = []
    
    for i in range(num_files):
        filename = f"file_{i}.py"
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"# File {i}\n")
        
        files.append(FileInfo(
            path=filename,
            name=filename,
            extension='.py',
            size=os.path.getsize(filepath)
        ))
    
    # Generate tree
    tree = f"{Path(temp_dir).name}/\n"
    for f in files:
        tree += f"├── {f.name}\n"
    
    structure = ProjectStructure(
        root_path=temp_dir,
        files=files,
        directories=[],
        tree=tree
    )
    
    return temp_dir, structure


@st.composite
def build_context_strategy(draw):
    """Generate a random BuildContext."""
    project_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters=' -_')))
    description = draw(st.text(min_size=10, max_size=200))
    project_type = draw(project_type_strategy())
    temp_dir, structure = draw(project_structure_strategy())
    dependencies = draw(dependencies_strategy())
    scripts = draw(scripts_strategy())
    languages = draw(st.lists(language_strategy(), min_size=1, max_size=5))
    
    # Generate diagrams
    diagrams = {}
    if draw(st.booleans()):
        diagrams['workflow'] = "```mermaid\nflowchart TD\n    A --> B\n```"
    if draw(st.booleans()):
        diagrams['architecture'] = "```mermaid\ngraph TB\n    A --> B\n```"
    
    context = BuildContext(
        project_name=project_name,
        description=description,
        project_type=project_type,
        structure=structure,
        dependencies=dependencies,
        scripts=scripts,
        languages=languages,
        diagrams=diagrams
    )
    
    return temp_dir, context


# Property 9: Required sections presence
# Feature: readme-generator, Property 9: Required sections presence
# Validates: Requirements 5.1

class TestRequiredSectionsPresence:
    """Test that generated README contains all required sections"""
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_detailed_template_contains_all_sections(self, context_data):
        """For any build context with detailed template, all required sections should be present"""
        temp_dir, context = context_data
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for required sections
            required_sections = [
                "# ",  # Header (project name)
                "## Features",
                "## Installation",
                "## Usage",
                "## Project Structure",
                "## Architecture",
                "## Scripts",
                "## Dependencies",
                "## Contributing",
                "## Screenshots",
                "## License"
            ]
            
            for section in required_sections:
                assert section in readme, \
                    f"Detailed README should contain '{section}' section"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_minimal_template_contains_basic_sections(self, context_data):
        """For any build context with minimal template, basic sections should be present"""
        temp_dir, context = context_data
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("minimal")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for basic sections
            basic_sections = [
                "# ",  # Header (project name)
                "## Installation",
                "## Usage"
            ]
            
            for section in basic_sections:
                assert section in readme, \
                    f"Minimal README should contain '{section}' section"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 10: Language-specific installation instructions
# Feature: readme-generator, Property 10: Language-specific installation instructions
# Validates: Requirements 5.2

class TestLanguageSpecificInstallation:
    """Test that installation instructions are appropriate for detected language"""
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_python_project_has_python_instructions(self, context_data):
        """For any Python project, installation should contain Python-specific commands"""
        temp_dir, context = context_data
        
        # Force Python project type
        context.project_type = ProjectType(language='Python', framework=None, config_files=[])
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for Python-specific commands
            python_indicators = [
                "pip install",
                "requirements.txt",
                "python -m venv"
            ]
            
            found_indicators = sum(1 for indicator in python_indicators if indicator in readme)
            
            assert found_indicators >= 2, \
                f"Python project should contain Python-specific installation commands, found {found_indicators}"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_nodejs_project_has_nodejs_instructions(self, context_data):
        """For any Node.js project, installation should contain Node.js-specific commands"""
        temp_dir, context = context_data
        
        # Force Node.js project type
        context.project_type = ProjectType(language='Node.js', framework=None, config_files=[])
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for Node.js-specific commands
            nodejs_indicators = [
                "npm install",
                "yarn install",
                "Node.js"
            ]
            
            found_indicators = sum(1 for indicator in nodejs_indicators if indicator in readme)
            
            assert found_indicators >= 1, \
                f"Node.js project should contain Node.js-specific installation commands"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_rust_project_has_rust_instructions(self, context_data):
        """For any Rust project, installation should contain Rust-specific commands"""
        temp_dir, context = context_data
        
        # Force Rust project type
        context.project_type = ProjectType(language='Rust', framework=None, config_files=[])
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for Rust-specific commands
            rust_indicators = [
                "cargo build",
                "Cargo",
                "Rust"
            ]
            
            found_indicators = sum(1 for indicator in rust_indicators if indicator in readme)
            
            assert found_indicators >= 2, \
                f"Rust project should contain Rust-specific installation commands"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 11: Hierarchical tree formatting
# Feature: readme-generator, Property 11: Hierarchical tree formatting
# Validates: Requirements 5.3

class TestHierarchicalTreeFormatting:
    """Test that project structure tree is properly formatted"""
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_structure_section_contains_tree(self, context_data):
        """For any project structure, the structure section should contain a tree view"""
        temp_dir, context = context_data
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check that structure section exists and contains tree
            assert "## Project Structure" in readme, \
                "README should contain Project Structure section"
            
            # Extract structure section
            structure_match = re.search(r'## Project Structure\n\n```\n(.*?)\n```', readme, re.DOTALL)
            
            assert structure_match is not None, \
                "Structure section should contain a code block with tree"
            
            tree_content = structure_match.group(1)
            
            # Tree should not be empty
            assert len(tree_content) > 0, \
                "Tree content should not be empty"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 12: Extracted data formatting
# Feature: readme-generator, Property 12: Extracted data formatting
# Validates: Requirements 5.4, 5.5

class TestExtractedDataFormatting:
    """Test that dependencies and scripts are properly formatted"""
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_dependencies_formatted_as_table(self, context_data):
        """For any dependencies, they should be formatted as a table"""
        temp_dir, context = context_data
        
        # Ensure we have some dependencies
        if not context.dependencies.runtime and not context.dependencies.development:
            context.dependencies.runtime = [
                Dependency(name="test-package", version="1.0.0", dev=False)
            ]
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for table formatting
            assert "## Dependencies" in readme, \
                "README should contain Dependencies section"
            
            # Should contain table markers
            assert "| Package | Version |" in readme or "No dependencies found" in readme, \
                "Dependencies should be formatted as a table or indicate none found"
            
            # If we have dependencies, check they're in the table
            if context.dependencies.runtime:
                for dep in context.dependencies.runtime[:3]:  # Check first 3
                    assert dep.name in readme, \
                        f"Dependency {dep.name} should appear in README"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_scripts_formatted_as_table(self, context_data):
        """For any scripts, they should be formatted as a table"""
        temp_dir, context = context_data
        
        # Ensure we have some scripts
        if not context.scripts.items:
            context.scripts.items = [
                Script(name="test", command="pytest", description="Run tests")
            ]
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for table formatting
            assert "## Scripts" in readme, \
                "README should contain Scripts section"
            
            # Should contain table markers
            assert "| Script | Command | Description |" in readme or "No scripts defined" in readme, \
                "Scripts should be formatted as a table or indicate none found"
            
            # If we have scripts, check they're in the table
            if context.scripts.items:
                for script in context.scripts.items[:3]:  # Check first 3
                    assert script.name in readme, \
                        f"Script {script.name} should appear in README"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 13: Usage section with examples
# Feature: readme-generator, Property 13: Usage section with examples
# Validates: Requirements 5.6

class TestUsageSectionWithExamples:
    """Test that usage section contains code examples"""
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_usage_section_contains_code_examples(self, context_data):
        """For any generated README, usage section should contain code examples"""
        temp_dir, context = context_data
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for usage section
            assert "## Usage" in readme, \
                "README should contain Usage section"
            
            # Extract usage section
            usage_match = re.search(r'## Usage\n\n(.*?)(?=\n## |\Z)', readme, re.DOTALL)
            
            assert usage_match is not None, \
                "Usage section should exist"
            
            usage_content = usage_match.group(1)
            
            # Should contain code blocks
            assert "```" in usage_content, \
                "Usage section should contain code examples in code blocks"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 24: Placeholder content inclusion
# Feature: readme-generator, Property 24: Placeholder content inclusion
# Validates: Requirements 13.1, 13.2

class TestPlaceholderContentInclusion:
    """Test that README includes placeholder sections"""
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_screenshots_section_has_placeholders(self, context_data):
        """For any generated README, screenshots section should have placeholder markdown"""
        temp_dir, context = context_data
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for screenshots section
            assert "## Screenshots" in readme, \
                "README should contain Screenshots section"
            
            # Should contain placeholder image markdown
            assert "![" in readme and "](" in readme, \
                "Screenshots section should contain image markdown syntax"
            
            # Should contain placeholder comments
            assert "<!--" in readme and "-->" in readme, \
                "Screenshots section should contain placeholder comments"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 25: Usage subsections structure
# Feature: readme-generator, Property 25: Usage subsections structure
# Validates: Requirements 13.3

class TestUsageSubsectionsStructure:
    """Test that usage section has proper subsections"""
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_usage_has_subsections(self, context_data):
        """For any generated README, usage section should have subsections"""
        temp_dir, context = context_data
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for usage subsections
            assert "### Basic Usage" in readme, \
                "Usage section should have Basic Usage subsection"
            
            assert "### Common Use Cases" in readme, \
                "Usage section should have Common Use Cases subsection"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 26: Contributing guidelines completeness
# Feature: readme-generator, Property 26: Contributing guidelines completeness
# Validates: Requirements 13.4

class TestContributingGuidelinesCompleteness:
    """Test that contributing section includes all required guidelines"""
    
    @given(context_data=build_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_contributing_has_all_guidelines(self, context_data):
        """For any generated README, contributing section should include PR, code style, and testing guidelines"""
        temp_dir, context = context_data
        
        try:
            builder = READMEBuilder()
            template_engine = TemplateEngine()
            template = template_engine.get_template("detailed")
            
            # Generate README
            readme = builder.build_readme(context, template)
            
            # Check for contributing section
            assert "## Contributing" in readme, \
                "README should contain Contributing section"
            
            # Check for required subsections
            required_subsections = [
                "### Pull Requests",
                "### Code Style",
                "### Testing"
            ]
            
            for subsection in required_subsections:
                assert subsection in readme, \
                    f"Contributing section should contain '{subsection}' subsection"
            
            # Check for key content
            assert "Fork the repository" in readme or "fork" in readme.lower(), \
                "Contributing should mention forking"
            
            assert "Pull Request" in readme or "PR" in readme, \
                "Contributing should mention pull requests"
            
            assert "test" in readme.lower(), \
                "Contributing should mention testing"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
