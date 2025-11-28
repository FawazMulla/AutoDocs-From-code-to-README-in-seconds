# Design Document: README Generator

## Overview

The README Generator is a web-based application that automates the creation of professional README documentation for software projects. The system analyzes project structure, detects technologies, extracts dependencies, and generates customized documentation in multiple formats. It supports both local filesystem projects and remote Git repositories, providing a seamless experience for developers who need to quickly generate comprehensive documentation.

The architecture follows a client-server model with a Flask backend handling project analysis and a modern web frontend providing an intuitive user interface. The core scanning engine uses pattern matching and file analysis to extract project metadata, which is then transformed into formatted markdown documentation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Frontend (HTML/CSS/JS)              │
│  - Input validation and user interaction                    │
│  - Real-time preview rendering                              │
│  - File operations (copy, download, save)                   │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/JSON
┌────────────────────▼────────────────────────────────────────┐
│                  Flask Backend (Python)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Routes                                          │   │
│  │  - /generate (POST) - Trigger scanning               │   │
│  │  - /save (POST) - Save README to filesystem          │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  DeepScanner Engine                                  │   │
│  │  - setup_path() - Handle local/remote repos          │   │
│  │  - scan() - Orchestrate analysis                     │   │
│  │  - _scan_tree() - Analyze directory structure        │   │
│  │  - _analyze_code() - Extract code metadata           │   │
│  │  - build_markdown() - Generate documentation         │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Parsers & Extractors                                │   │
│  │  - _parse_package_json() - Node.js deps              │   │
│  │  - _parse_requirements() - Python deps               │   │
│  │  - _analyze_code() - Language detection              │   │
│  │  - _scan_license() - License identification          │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │ File I/O
┌────────────────────▼────────────────────────────────────────┐
│              Filesystem & Git Operations                     │
│  - Local directory scanning                                 │
│  - Git repository cloning                                   │
│  - Temporary file management                                │
│  - README.md file writing                                   │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Frontend Components

**Input Controls**
- Path input field: Accepts local paths or Git URLs
- Template selector: Toggle between Detailed and Minimal templates
- Custom context textarea: Optional developer notes
- Action buttons: Generate, Copy, Download, Save

**Output Display**
- Live markdown preview with syntax highlighting
- Mermaid diagram rendering
- Terminal-style output log
- Copy/Download/Save action buttons

### 2. Backend API Routes

**POST /generate**
- Input: `{ path: string, template: string, context: string }`
- Output: `{ success: boolean, markdown: string, error?: string }`
- Triggers DeepScanner analysis and markdown generation

**POST /save**
- Input: `{ path: string, content: string }`
- Output: `{ success: boolean, error?: string }`
- Writes README.md to specified directory

### 3. DeepScanner Class

**Core Methods**
- `__init__(path, custom_context)`: Initialize scanner with project path
- `setup_path()`: Handle local/remote repository setup
- `scan()`: Execute full project analysis
- `build_markdown(template)`: Generate markdown documentation
- `cleanup()`: Clean up temporary resources

**Analysis Methods**
- `_scan_tree(root_path)`: Build project structure tree
- `_analyze_code(filepath, ext)`: Extract code metadata
- `_parse_package_json(filepath)`: Parse Node.js dependencies
- `_parse_requirements(filepath)`: Parse Python dependencies
- `_scan_license()`: Detect license type
- `generate_diagrams()`: Create Mermaid architecture diagrams

### 4. Metadata Structure

```python
metadata = {
    "project_name": str,
    "username": str,
    "repo_name": str,
    "repo_url": str,
    "languages": set,  # {Python, Node.js, Java, Go}
    "tech_stack": set,
    "dependencies": {
        "Python": set,
        "Node.js": set,
        "Java": set,
        "Go": set
    },
    "scripts": dict,
    "structure": str,  # Tree view
    "description": str,
    "entry_point": str,  # Main file
    "entry_point_cmd": str,  # Main class
    "api_endpoints": list,
    "license": str,
    "modules": list,  # Classes/modules
    "env_vars": set,
    "tests": list,
    "build_tools": set  # Maven, Gradle, etc.
}
```

## Data Models

### Project Metadata
- **Languages**: Set of detected programming languages
- **Dependencies**: Organized by language with standard library filtering
- **Entry Points**: Primary file and class/function for application startup
- **Build Tools**: Maven, Gradle, npm, pip, go mod
- **License**: Detected from LICENSE file or defaulted to "Unlicensed"

### Configuration Files Parsed
- `package.json`: Node.js project metadata and dependencies
- `requirements.txt`: Python dependencies
- `pom.xml`: Java Maven configuration
- `build.gradle`: Java Gradle configuration
- `go.mod`: Go module dependencies
- `LICENSE`: Project license information

### Generated Documentation
- **Detailed Template**: Comprehensive README with all sections
- **Minimal Template**: Concise README with essential sections
- **Custom Context**: Developer-provided notes integrated into documentation

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Local Path Analysis Completeness
*For any* valid local directory path, scanning it SHALL extract metadata including at least one language, project name, and structure without errors.
**Validates: Requirements 1.1**

### Property 2: Remote Repository Cloning and Cleanup
*For any* valid remote Git repository URL, cloning and analyzing it SHALL succeed, and temporary files SHALL be cleaned up after analysis completes.
**Validates: Requirements 1.2**

### Property 3: Invalid Path Error Handling
*For any* invalid or non-existent path, the system SHALL return an error message and NOT modify any existing state.
**Validates: Requirements 1.3**

### Property 4: Language Detection Accuracy
*For any* project containing language-specific configuration files (package.json, requirements.txt, pom.xml), the system SHALL correctly identify the corresponding language.
**Validates: Requirements 2.1, 2.2, 2.3**

### Property 5: Standard Library Filtering
*For any* code file analyzed, standard library imports SHALL be excluded from the extracted dependencies list.
**Validates: Requirements 3.3**

### Property 6: Entry Point Detection
*For any* project with a single entry point, the system SHALL correctly identify it; when multiple entry points exist, the system SHALL select the most likely primary one.
**Validates: Requirements 4.1, 4.2, 4.3**

### Property 7: Architecture Diagram Validity
*For any* generated architecture diagram, the output SHALL contain valid Mermaid syntax that renders without errors.
**Validates: Requirements 5.1, 5.2, 5.3**

### Property 8: Template Differentiation
*For any* project, generating a Detailed template SHALL produce more sections than a Minimal template.
**Validates: Requirements 6.1, 6.2**

### Property 9: Custom Context Inclusion
*For any* non-empty custom context provided, the generated README SHALL include it; when context is empty, the README SHALL NOT include a context section.
**Validates: Requirements 6.3, 13.2**

### Property 10: Installation Instructions Language-Specific
*For any* project using a specific language (Node.js, Python, Java), the generated installation instructions SHALL include language-appropriate commands.
**Validates: Requirements 7.1, 7.2, 7.3**

### Property 11: Usage Instructions Accuracy
*For any* project with a detected entry point, the generated usage instructions SHALL include the correct startup command for that language.
**Validates: Requirements 8.1, 8.2, 8.3**

### Property 12: File I/O Operations
*For any* generated markdown content, copying it SHALL preserve all content; downloading it SHALL create a valid file; saving to remote paths SHALL be rejected.
**Validates: Requirements 9.1, 9.2, 9.3**

### Property 13: Error Handling Robustness
*For any* error condition (empty path, clone failure, file read error), the system SHALL display an appropriate error message and continue operation.
**Validates: Requirements 10.1, 10.2, 10.3**

### Property 14: Project Structure Tree Depth
*For any* project with nested directories, the generated tree view SHALL limit depth to 4 levels and exclude ignored directories.
**Validates: Requirements 11.1, 11.2, 11.3**

### Property 15: License Detection
*For any* project with a LICENSE file, the system SHALL identify the license type; when no LICENSE exists, it SHALL default to "Unlicensed".
**Validates: Requirements 12.1, 12.2, 12.3**

### Property 16: Special Character Handling
*For any* custom context containing special characters, the system SHALL properly escape them in the generated markdown.
**Validates: Requirements 13.3**

### Property 17: GitHub Metadata Extraction
*For any* Git repository, the system SHALL extract the repository URL and username; when metadata is unavailable, it SHALL display language badges instead.
**Validates: Requirements 14.1, 14.2, 14.3**

### Property 18: Parser Round-Trip Consistency
*For any* configuration file (package.json, requirements.txt), parsing and serializing it SHALL preserve all essential information without loss.
**Validates: Requirements 15.1, 15.2, 15.3**

## Error Handling

### Input Validation
- Empty path: Return 400 error with "Path is required" message
- Invalid path format: Return 400 error with descriptive message
- Remote path for save operation: Return 400 error with "Remote repos cannot be saved locally" message

### File Operations
- Directory not found: Return 400 error with "Directory not found" message
- File read errors: Log error and continue scanning other files
- File write errors: Return 500 error with exception message

### Git Operations
- Clone failure: Return 500 error with "Clone failed: {error}" message
- Repository access denied: Return 500 error with appropriate message

### Resource Management
- Temporary directory cleanup: Use try-finally to ensure cleanup even on errors
- File handle management: Use context managers for all file operations
- Memory management: Clean up large objects after use

## Testing Strategy

### Unit Testing Approach
- Test individual parser functions (package.json, requirements.txt)
- Test language detection logic with various file combinations
- Test entry point detection with different code patterns
- Test error handling for invalid inputs
- Test file I/O operations with mock filesystem

### Property-Based Testing Approach
- Use Python's `hypothesis` library for property-based testing
- Generate random project structures and verify scanning completeness
- Generate random dependency lists and verify filtering accuracy
- Generate random paths and verify error handling
- Generate random markdown content and verify round-trip consistency
- Configure each property test to run minimum 100 iterations

### Test Organization
- Unit tests: `tests/test_parsers.py`, `tests/test_detection.py`, `tests/test_io.py`
- Property tests: `tests/test_properties.py`
- Integration tests: `tests/test_integration.py`
- Test fixtures: `tests/fixtures/` with sample projects

### Coverage Goals
- Core scanning logic: 90%+ coverage
- Parser functions: 95%+ coverage
- Error handling: 85%+ coverage
- API routes: 80%+ coverage

