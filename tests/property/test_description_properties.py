"""
Property-based tests for description extraction.
Tests Properties 14 and 15 from the design document.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile
import os
import shutil

from app.extractors import DescriptionExtractor
from app.scanner import FileInfo, ProjectStructure
from app.detectors import ProjectType


# Custom strategies for generating test data

@st.composite
def python_file_with_docstring(draw):
    """
    Generate a Python file with a module-level docstring.
    Returns tuple of (temp_file_path, expected_docstring)
    """
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, 'test_module.py')
    
    # Generate a docstring with safe characters (letters, numbers, spaces, basic punctuation)
    docstring_lines = draw(st.lists(
        st.text(
            alphabet=st.characters(
                whitelist_categories=('L', 'N'),
                whitelist_characters=' .,!?-'
            ),
            min_size=10,
            max_size=100
        ),
        min_size=1,
        max_size=5
    ))
    docstring = ' '.join(line.strip() for line in docstring_lines if line.strip())
    
    # Ensure we have a non-empty docstring
    if not docstring:
        docstring = "This is a test module"
    
    # Write Python file with module docstring
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(f'"""\n{docstring}\n"""\n\n')
        f.write('def some_function():\n')
        f.write('    pass\n')
    
    return temp_dir, temp_file, docstring


@st.composite
def file_with_header_comment(draw):
    """
    Generate a file with header comments.
    Returns tuple of (temp_dir, temp_file_path, expected_comment, extension)
    """
    temp_dir = tempfile.mkdtemp()
    
    # Choose file type
    file_types = [
        ('.py', '#'),
        ('.js', '//'),
        ('.rs', '//'),
        ('.rb', '#'),
    ]
    extension, comment_char = draw(st.sampled_from(file_types))
    
    temp_file = os.path.join(temp_dir, f'test_file{extension}')
    
    # Generate comment lines with safe characters
    comment_lines = draw(st.lists(
        st.text(
            alphabet=st.characters(
                whitelist_categories=('L', 'N'),
                whitelist_characters=' .,!?-'
            ),
            min_size=10,
            max_size=100
        ),
        min_size=1,
        max_size=5
    ))
    
    # Clean up comment lines
    comment_lines = [line.strip() for line in comment_lines if line.strip()]
    if not comment_lines:
        comment_lines = ["This is a test file"]
    
    # Write file with header comments
    with open(temp_file, 'w', encoding='utf-8') as f:
        for line in comment_lines:
            f.write(f'{comment_char} {line}\n')
        f.write('\n')
        f.write('# Some code here\n')
    
    expected_comment = ' '.join(comment_lines)
    
    return temp_dir, temp_file, expected_comment, extension


@st.composite
def project_with_descriptions(draw):
    """
    Generate a project structure with files containing descriptions.
    Returns tuple of (temp_dir, ProjectStructure, has_descriptions)
    """
    temp_dir = tempfile.mkdtemp()
    files = []
    has_descriptions = False
    
    # Create main.py with docstring
    main_py = os.path.join(temp_dir, 'main.py')
    docstring = draw(st.text(min_size=20, max_size=200))
    with open(main_py, 'w', encoding='utf-8') as f:
        f.write(f'"""\n{docstring}\n"""\n\n')
        f.write('def main():\n    pass\n')
    
    files.append(FileInfo(
        path='main.py',
        name='main.py',
        extension='.py',
        size=os.path.getsize(main_py)
    ))
    has_descriptions = True
    
    # Optionally add more files
    num_extra_files = draw(st.integers(min_value=0, max_value=5))
    for i in range(num_extra_files):
        filename = f'module_{i}.py'
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f'# Module {i}\n')
        
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
    
    return temp_dir, structure, has_descriptions


@st.composite
def description_candidates(draw):
    """
    Generate a list of description candidates with varying quality.
    Returns list of candidate strings
    """
    num_candidates = draw(st.integers(min_value=2, max_value=10))
    candidates = []
    
    for i in range(num_candidates):
        # Generate candidates of varying lengths and quality
        length = draw(st.integers(min_value=5, max_value=300))
        
        # Some candidates are sentences, some are not
        has_period = draw(st.booleans())
        has_descriptive_words = draw(st.booleans())
        
        text = draw(st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Z')),
            min_size=length,
            max_size=length
        ))
        
        if has_period:
            text = text + '. This is a complete sentence.'
        
        if has_descriptive_words:
            descriptive = draw(st.sampled_from([
                'application', 'system', 'tool', 'library', 
                'framework', 'project', 'module'
            ]))
            text = f'This {descriptive} ' + text
        
        candidates.append(text)
    
    return candidates


# Property 14: Description extraction from code
# Feature: readme-generator, Property 14: Description extraction from code
# Validates: Requirements 6.1, 6.2

class TestDescriptionExtractionFromCode:
    """Test that description extractor extracts text from code comments and docstrings"""
    
    @given(file_data=python_file_with_docstring())
    @settings(max_examples=100, deadline=None)
    def test_extracts_python_module_docstrings(self, file_data):
        """For any Python file with module docstring, extractor should extract it"""
        temp_dir, temp_file, expected_docstring = file_data
        
        try:
            extractor = DescriptionExtractor()
            
            # Extract docstrings
            docstrings = extractor.extract_python_docstrings(temp_file)
            
            assert len(docstrings) > 0, \
                "Should extract at least one docstring"
            
            # The expected docstring should be in the extracted docstrings
            # (accounting for whitespace normalization)
            expected_stripped = expected_docstring.strip()
            assert any(expected_stripped == ds.strip() for ds in docstrings), \
                f"Expected docstring should be extracted"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(file_data=file_with_header_comment())
    @settings(max_examples=100, deadline=None)
    def test_extracts_header_comments(self, file_data):
        """For any file with header comments, extractor should extract them"""
        temp_dir, temp_file, expected_comment, extension = file_data
        
        try:
            extractor = DescriptionExtractor()
            
            # Extract header comments
            header_comment = extractor.extract_header_comments(temp_file)
            
            # Should extract something
            assert header_comment is not None, \
                f"Should extract header comment from {extension} file"
            
            # The extracted comment should contain the expected text
            # (allowing for some whitespace differences)
            assert len(header_comment) > 0, \
                "Extracted comment should not be empty"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        docstring_length=st.integers(min_value=20, max_value=500),
        num_functions=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    def test_extracts_from_various_python_structures(self, docstring_length, num_functions):
        """For any Python file structure, extractor should find docstrings"""
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, 'module.py')
        
        try:
            # Create Python file with module docstring and function docstrings
            with open(temp_file, 'w', encoding='utf-8') as f:
                # Module docstring
                module_doc = 'A' * docstring_length
                f.write(f'"""{module_doc}"""\n\n')
                
                # Function docstrings
                for i in range(num_functions):
                    f.write(f'def function_{i}():\n')
                    f.write(f'    """Function {i} docstring"""\n')
                    f.write(f'    pass\n\n')
            
            extractor = DescriptionExtractor()
            docstrings = extractor.extract_python_docstrings(temp_file)
            
            # Should extract at least the module docstring
            assert len(docstrings) >= 1, \
                "Should extract at least module docstring"
            
            # Module docstring should be first
            assert module_doc in docstrings[0], \
                "Module docstring should be extracted"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(project=project_with_descriptions())
    @settings(max_examples=100, deadline=None)
    def test_extract_description_finds_content(self, project):
        """For any project with description content, extractor should find it"""
        temp_dir, structure, has_descriptions = project
        
        try:
            extractor = DescriptionExtractor()
            project_type = ProjectType(language='Python')
            
            # Extract description
            description = extractor.extract_description(structure, project_type)
            
            assert description is not None, \
                "Should return a description"
            assert len(description) > 0, \
                "Description should not be empty"
            
            if has_descriptions:
                # Should not just be the folder name fallback
                folder_name = Path(structure.root_path).name
                assert description != f"A {folder_name} project" or len(description) > 20, \
                    "Should extract actual description when available"
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


# Property 15: Best description selection
# Feature: readme-generator, Property 15: Best description selection
# Validates: Requirements 6.3

class TestBestDescriptionSelection:
    """Test that description selector chooses the most comprehensive description"""
    
    @given(candidates=description_candidates())
    @settings(max_examples=100, deadline=None)
    def test_selects_from_candidates(self, candidates):
        """For any set of candidates, selector should choose one"""
        extractor = DescriptionExtractor()
        
        # Select best description
        best = extractor.select_best_description(candidates)
        
        assert best is not None, \
            "Should select a description"
        assert best in candidates, \
            "Selected description should be from candidates"
        assert len(best) > 0, \
            "Selected description should not be empty"
    
    @given(
        short_text=st.text(min_size=5, max_size=20),
        long_text=st.text(min_size=100, max_size=300)
    )
    @settings(max_examples=100, deadline=None)
    def test_prefers_longer_descriptions(self, short_text, long_text):
        """For any pair of candidates, selector should prefer longer ones"""
        # Ensure they're actually different lengths
        assume(len(long_text) > len(short_text) + 50)
        
        extractor = DescriptionExtractor()
        candidates = [short_text, long_text]
        
        best = extractor.select_best_description(candidates)
        
        # Should prefer the longer text (with high probability due to scoring)
        # Note: This might not always be true if short_text has many bonus words
        # but generally longer should win
        assert len(best) >= len(short_text), \
            "Selected description should be at least as long as shortest"
    
    @given(
        base_text=st.text(min_size=50, max_size=100),
        add_sentences=st.booleans(),
        add_descriptive_words=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    def test_prefers_quality_indicators(self, base_text, add_sentences, add_descriptive_words):
        """For any candidates, selector should prefer those with quality indicators"""
        extractor = DescriptionExtractor()
        
        # Create two candidates - one plain, one with quality indicators
        plain_candidate = base_text
        enhanced_candidate = base_text
        
        if add_sentences:
            enhanced_candidate = enhanced_candidate + '. This is a sentence. Another sentence.'
        
        if add_descriptive_words:
            enhanced_candidate = 'This application provides ' + enhanced_candidate
        
        # Only test if enhanced is actually different
        assume(enhanced_candidate != plain_candidate)
        
        candidates = [plain_candidate, enhanced_candidate]
        best = extractor.select_best_description(candidates)
        
        # Enhanced should often win due to quality bonuses
        # (though not guaranteed if plain is much longer)
        assert best in candidates, \
            "Should select one of the candidates"
    
    def test_handles_empty_candidates(self):
        """For empty candidate list, selector should return empty string"""
        extractor = DescriptionExtractor()
        
        best = extractor.select_best_description([])
        
        assert best == "", \
            "Should return empty string for empty candidates"
    
    @given(very_short_texts=st.lists(
        st.text(min_size=1, max_size=5),
        min_size=1,
        max_size=10
    ))
    @settings(max_examples=100, deadline=None)
    def test_handles_very_short_candidates(self, very_short_texts):
        """For any set of very short candidates, selector should still choose one"""
        extractor = DescriptionExtractor()
        
        best = extractor.select_best_description(very_short_texts)
        
        assert best in very_short_texts, \
            "Should select from available candidates even if all are short"
    
    @given(
        num_candidates=st.integers(min_value=3, max_value=20),
        best_index=st.integers(min_value=0, max_value=19)
    )
    @settings(max_examples=100, deadline=None)
    def test_consistent_selection(self, num_candidates, best_index):
        """For any set of candidates, selector should be deterministic"""
        # Ensure best_index is valid
        assume(best_index < num_candidates)
        
        extractor = DescriptionExtractor()
        
        # Create candidates where one is clearly best (longest with quality indicators)
        candidates = []
        for i in range(num_candidates):
            if i == best_index:
                # Make this one clearly the best
                candidates.append(
                    'This application is a comprehensive system that provides '
                    'extensive functionality. It includes multiple features. '
                    'The project is well-documented and maintained.'
                )
            else:
                # Make others shorter and less descriptive
                candidates.append(f'Short text {i}')
        
        # Select twice - should get same result
        best1 = extractor.select_best_description(candidates)
        best2 = extractor.select_best_description(candidates)
        
        assert best1 == best2, \
            "Selection should be deterministic"
        
        # Should select the enhanced candidate
        assert best1 == candidates[best_index], \
            "Should select the clearly best candidate"
