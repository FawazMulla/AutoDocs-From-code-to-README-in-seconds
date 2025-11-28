"""
Property-based tests for diagram generation.
Tests Properties 22 and 23 from the design document.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile
import os
import shutil
import re

from app.generators import DiagramGenerator
from app.detectors import ProjectType
from app.scanner import FileInfo, ProjectStructure


# Custom strategies for generating test data

@st.composite
def project_structure_with_components(draw):
    """
    Generate a project structure with various components.
    Returns tuple of (temp_dir, ProjectStructure, expected_components)
    """
    temp_dir = tempfile.mkdtemp()
    
    # Common component directory names
    component_types = [
        'api', 'routes', 'controllers', 'handlers',
        'models', 'schemas', 'entities',
        'services', 'business', 'logic',
        'repositories', 'database', 'db',
        'views', 'templates', 'ui', 'components',
        'middleware', 'utils', 'helpers',
        'tests', 'config', 'auth',
        'validators', 'extractors', 'parsers',
        'builders', 'generators', 'detectors'
    ]
    
    # Select random components to include
    num_components = draw(st.integers(min_value=0, max_value=10))
    selected_components = draw(st.lists(
        st.sampled_from(component_types),
        min_size=num_components,
        max_size=num_components,
        unique=True
    ))
    
    files = []
    directories = []
    
    # Create component directories with files
    for component in selected_components:
        comp_dir = os.path.join(temp_dir, component)
        os.makedirs(comp_dir, exist_ok=True)
        directories.append(component)
        
        # Add a Python file to the component
        filename = f"{component}_module.py"
        filepath = os.path.join(comp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"# {component} module\n")
        
        files.append(FileInfo(
            path=os.path.join(component, filename),
            name=filename,
            extension='.py',
            size=os.path.getsize(filepath)
        ))
    
    structure = ProjectStructure(
        root_path=temp_dir,
        files=files,
        directories=directories,
        tree=""
    )
    
    return temp_dir, structure, selected_components


@st.composite
def simple_project_structure(draw):
    """
    Generate a simple project structure with few or no components.
    Returns tuple of (temp_dir, ProjectStructure)
    """
    temp_dir = tempfile.mkdtemp()
    
    files = []
    
    # Add a few simple files
    num_files = draw(st.integers(min_value=1, max_value=5))
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
    
    structure = ProjectStructure(
        root_path=temp_dir,
        files=files,
        directories=[],
        tree=""
    )
    
    return temp_dir, structure


@st.composite
def project_type_strategy(draw):
    """Generate a random ProjectType."""
    languages = ['Python', 'Node.js', 'Rust', 'Go', 'Java']
    frameworks = [None, 'Django', 'Flask', 'React', 'Express', 'Vue']
    
    language = draw(st.sampled_from(languages))
    framework = draw(st.sampled_from(frameworks))
    
    return ProjectType(
        language=language,
        framework=framework,
        config_files=[]
    )


# Property 22: Mermaid diagram inclusion
# Feature: readme-generator, Property 22: Mermaid diagram inclusion
# Validates: Requirements 12.1, 12.2

class TestMermaidDiagramInclusion:
    """Test that generated diagrams include valid Mermaid syntax"""
    
    @given(
        project=project_structure_with_components(),
        project_type=project_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_workflow_diagram_contains_mermaid_syntax(self, project, project_type):
        """For any project structure, workflow diagram should contain Mermaid syntax"""
        temp_dir, structure, components = project
        
        try:
            generator = DiagramGenerator()
            
            # Generate workflow diagram
            diagram = generator.generate_workflow_diagram(project_type, structure)
            
            # Should contain Mermaid code block markers
            assert '```mermaid' in diagram, \
                "Diagram should start with Mermaid code block"
            assert '```' in diagram[10:], \
                "Diagram should end with closing code block marker"
            
            # Should contain flowchart or graph declaration
            assert 'flowchart' in diagram or 'graph' in diagram, \
                "Diagram should contain flowchart or graph declaration"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        project=project_structure_with_components(),
        project_type=project_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_architecture_diagram_contains_mermaid_syntax(self, project, project_type):
        """For any project with components, architecture diagram should contain Mermaid syntax"""
        temp_dir, structure, components = project
        
        try:
            generator = DiagramGenerator()
            detected_components = generator.detect_components(structure)
            
            # Generate architecture diagram
            diagram = generator.generate_architecture_diagram(detected_components)
            
            # Should contain Mermaid code block markers
            assert '```mermaid' in diagram, \
                "Diagram should start with Mermaid code block"
            assert '```' in diagram[10:], \
                "Diagram should end with closing code block marker"
            
            # Should contain graph declaration
            assert 'graph' in diagram, \
                "Architecture diagram should contain graph declaration"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        project=simple_project_structure(),
        project_type=project_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_simple_project_generates_diagram(self, project, project_type):
        """For any simple project, a diagram should still be generated"""
        temp_dir, structure = project
        
        try:
            generator = DiagramGenerator()
            
            # Generate workflow diagram for simple project
            diagram = generator.generate_workflow_diagram(project_type, structure)
            
            # Should still contain Mermaid syntax
            assert '```mermaid' in diagram, \
                "Simple project should still generate Mermaid diagram"
            assert 'flowchart' in diagram or 'graph' in diagram, \
                "Simple project diagram should have flowchart or graph"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(project=project_structure_with_components())
    @settings(max_examples=100, deadline=None)
    def test_component_detection_returns_list(self, project):
        """For any project structure, component detection should return a list"""
        temp_dir, structure, expected_components = project
        
        try:
            generator = DiagramGenerator()
            
            # Detect components
            detected = generator.detect_components(structure)
            
            # Should return a list
            assert isinstance(detected, list), \
                "Component detection should return a list"
            
            # All items should be strings
            for component in detected:
                assert isinstance(component, str), \
                    f"Component {component} should be a string"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 23: Mermaid syntax validity
# Feature: readme-generator, Property 23: Mermaid syntax validity
# Validates: Requirements 12.3

class TestMermaidSyntaxValidity:
    """Test that generated Mermaid diagrams have valid syntax"""
    
    def _validate_mermaid_syntax(self, diagram: str) -> bool:
        """
        Basic validation of Mermaid syntax.
        Checks for common syntax requirements.
        """
        # Should have code block markers
        if '```mermaid' not in diagram:
            return False
        
        # Extract the Mermaid content
        match = re.search(r'```mermaid\n(.*?)\n```', diagram, re.DOTALL)
        if not match:
            return False
        
        mermaid_content = match.group(1)
        
        # Should have a diagram type declaration
        if not any(keyword in mermaid_content for keyword in ['flowchart', 'graph', 'sequenceDiagram', 'classDiagram']):
            return False
        
        # Should have at least one node or connection
        # Nodes are typically: A[Label] or A(Label) or A{Label}
        # Connections are: --> or --- or -.->
        has_nodes = bool(re.search(r'[A-Z]\d*\[.*?\]|[A-Z]\d*\(.*?\)|[A-Z]\d*\{.*?\}', mermaid_content))
        has_connections = bool(re.search(r'-->|---|\.\.>|==>|-\.->', mermaid_content))
        
        return has_nodes or has_connections
    
    @given(
        project=project_structure_with_components(),
        project_type=project_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_workflow_diagram_has_valid_syntax(self, project, project_type):
        """For any project, workflow diagram should have valid Mermaid syntax"""
        temp_dir, structure, components = project
        
        try:
            generator = DiagramGenerator()
            
            # Generate workflow diagram
            diagram = generator.generate_workflow_diagram(project_type, structure)
            
            # Validate syntax
            assert self._validate_mermaid_syntax(diagram), \
                f"Workflow diagram should have valid Mermaid syntax:\n{diagram}"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(project=project_structure_with_components())
    @settings(max_examples=100, deadline=None)
    def test_architecture_diagram_has_valid_syntax(self, project):
        """For any project, architecture diagram should have valid Mermaid syntax"""
        temp_dir, structure, components = project
        
        try:
            generator = DiagramGenerator()
            detected_components = generator.detect_components(structure)
            
            # Generate architecture diagram
            diagram = generator.generate_architecture_diagram(detected_components)
            
            # Validate syntax
            assert self._validate_mermaid_syntax(diagram), \
                f"Architecture diagram should have valid Mermaid syntax:\n{diagram}"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        project=simple_project_structure(),
        project_type=project_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_simple_project_diagram_has_valid_syntax(self, project, project_type):
        """For any simple project, diagram should have valid Mermaid syntax"""
        temp_dir, structure = project
        
        try:
            generator = DiagramGenerator()
            
            # Generate workflow diagram
            diagram = generator.generate_workflow_diagram(project_type, structure)
            
            # Validate syntax
            assert self._validate_mermaid_syntax(diagram), \
                f"Simple project diagram should have valid Mermaid syntax:\n{diagram}"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        project=project_structure_with_components(),
        project_type=project_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_diagram_has_proper_code_block_structure(self, project, project_type):
        """For any generated diagram, code blocks should be properly formatted"""
        temp_dir, structure, components = project
        
        try:
            generator = DiagramGenerator()
            
            # Generate workflow diagram
            diagram = generator.generate_workflow_diagram(project_type, structure)
            
            # Count opening and closing markers
            opening_markers = diagram.count('```mermaid')
            closing_markers = diagram.count('```') - opening_markers  # Subtract opening markers
            
            assert opening_markers == 1, \
                f"Should have exactly one opening marker, found {opening_markers}"
            assert closing_markers == 1, \
                f"Should have exactly one closing marker, found {closing_markers}"
            
            # Opening marker should come before closing
            opening_pos = diagram.find('```mermaid')
            closing_pos = diagram.rfind('```')
            
            assert opening_pos < closing_pos, \
                "Opening marker should come before closing marker"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(project=project_structure_with_components())
    @settings(max_examples=100, deadline=None)
    def test_diagram_nodes_have_valid_identifiers(self, project):
        """For any generated diagram, node identifiers should be valid"""
        temp_dir, structure, components = project
        
        try:
            generator = DiagramGenerator()
            detected_components = generator.detect_components(structure)
            
            # Generate architecture diagram
            diagram = generator.generate_architecture_diagram(detected_components)
            
            # Extract Mermaid content
            match = re.search(r'```mermaid\n(.*?)\n```', diagram, re.DOTALL)
            if match:
                mermaid_content = match.group(1)
                
                # Find all node identifiers (letters followed by optional numbers)
                node_ids = re.findall(r'\b([A-Z]\d*)\b', mermaid_content)
                
                # All node IDs should be valid (single letter or letter + number)
                for node_id in node_ids:
                    assert re.match(r'^[A-Z]\d*$', node_id), \
                        f"Node ID {node_id} should be valid (letter + optional number)"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        num_components=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    def test_architecture_diagram_with_varying_component_counts(self, num_components):
        """For any number of components, architecture diagram should be valid"""
        # Create component list
        components = [f"Component{i}" for i in range(num_components)]
        
        generator = DiagramGenerator()
        
        # Generate architecture diagram
        diagram = generator.generate_architecture_diagram(components)
        
        # Should have valid Mermaid syntax
        assert self._validate_mermaid_syntax(diagram), \
            f"Architecture diagram with {num_components} components should be valid:\n{diagram}"
        
        # Should contain code block
        assert '```mermaid' in diagram
        assert '```' in diagram[10:]
    
    @given(
        project=project_structure_with_components(),
        project_type=project_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_workflow_diagram_contains_flow_direction(self, project, project_type):
        """For any workflow diagram, it should specify a flow direction"""
        temp_dir, structure, components = project
        
        try:
            generator = DiagramGenerator()
            
            # Generate workflow diagram
            diagram = generator.generate_workflow_diagram(project_type, structure)
            
            # Extract Mermaid content
            match = re.search(r'```mermaid\n(.*?)\n```', diagram, re.DOTALL)
            if match:
                mermaid_content = match.group(1)
                
                # Should have flowchart with direction (TD, LR, etc.) or graph with direction (TB, LR, etc.)
                has_direction = bool(re.search(r'flowchart\s+(TD|LR|RL|BT)|graph\s+(TB|LR|RL|BT)', mermaid_content))
                
                assert has_direction, \
                    "Workflow diagram should specify a flow direction (TD, LR, etc.)"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
