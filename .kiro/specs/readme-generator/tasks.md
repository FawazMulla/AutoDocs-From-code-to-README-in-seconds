# Implementation Plan: README Generator

## Phase 1: Core Infrastructure and Testing Framework

- [ ] 1. Set up testing infrastructure and test fixtures
  - Create `tests/` directory structure
  - Set up pytest and hypothesis for property-based testing
  - Create sample project fixtures (Python, Node.js, Java projects)
  - Create mock file structures for testing
  - _Requirements: 1.1, 1.2, 1.3_

- [ ]* 1.1 Write property test for local path analysis
  - **Feature: readme-generator, Property 1: Local Path Analysis Completeness**
  - **Validates: Requirements 1.1**

- [ ]* 1.2 Write property test for remote repository handling
  - **Feature: readme-generator, Property 2: Remote Repository Cloning and Cleanup**
  - **Validates: Requirements 1.2**

- [ ]* 1.3 Write property test for invalid path error handling
  - **Feature: readme-generator, Property 3: Invalid Path Error Handling**
  - **Validates: Requirements 1.3**

## Phase 2: Language and Dependency Detection

- [ ] 2. Implement language detection system
  - Create language detection logic for Python, Node.js, Java, Go
  - Implement configuration file detection (package.json, requirements.txt, pom.xml, go.mod)
  - Add language identification to metadata extraction
  - _Requirements: 2.1, 2.2, 2.3_

- [ ]* 2.1 Write property test for language detection
  - **Feature: readme-generator, Property 4: Language Detection Accuracy**
  - **Validates: Requirements 2.1, 2.2, 2.3**

- [ ] 3. Implement dependency extraction
  - Create parser for package.json (Node.js)
  - Create parser for requirements.txt (Python)
  - Implement standard library filtering for each language
  - Extract dependencies from code imports
  - _Requirements: 3.1, 3.2, 3.3_

- [ ]* 3.1 Write property test for standard library filtering
  - **Feature: readme-generator, Property 5: Standard Library Filtering**
  - **Validates: Requirements 3.3**

- [ ]* 3.2 Write unit tests for dependency parsers
  - Test package.json parsing with various formats
  - Test requirements.txt parsing with version specifiers
  - Test import statement extraction

## Phase 3: Entry Point and Architecture Detection

- [ ] 4. Implement entry point detection
  - Detect Python entry points (if __name__ == "__main__", app.run)
  - Detect Node.js entry points (app.listen, server.listen)
  - Detect Java entry points (public static void main)
  - Implement primary entry point selection logic
  - _Requirements: 4.1, 4.2, 4.3_

- [ ]* 4.1 Write property test for entry point detection
  - **Feature: readme-generator, Property 6: Entry Point Detection**
  - **Validates: Requirements 4.1, 4.2, 4.3**

- [ ] 5. Implement architecture diagram generation
  - Create Mermaid diagram generator for class-based architectures
  - Create Mermaid diagram generator for component-based architectures
  - Implement database detection and inclusion in diagrams
  - Validate Mermaid syntax generation
  - _Requirements: 5.1, 5.2, 5.3_

- [ ]* 5.1 Write property test for architecture diagram validity
  - **Feature: readme-generator, Property 7: Architecture Diagram Validity**
  - **Validates: Requirements 5.1, 5.2, 5.3**

## Phase 4: README Template Generation

- [ ] 6. Implement Detailed template generation
  - Create markdown builder for comprehensive README
  - Include all sections: description, architecture, structure, installation, usage, dependencies, contributing, license
  - Implement GitHub badge generation
  - _Requirements: 6.1, 6.2_

- [ ] 7. Implement Minimal template generation
  - Create markdown builder for concise README
  - Include essential sections: description, tech stack, installation, usage, license
  - Ensure Minimal template is shorter than Detailed
  - _Requirements: 6.1, 6.2_

- [ ]* 7.1 Write property test for template differentiation
  - **Feature: readme-generator, Property 8: Template Differentiation**
  - **Validates: Requirements 6.1, 6.2**

- [ ] 8. Implement custom context integration
  - Add custom context to both templates
  - Implement context inclusion/omission logic
  - Handle special character escaping in markdown
  - _Requirements: 6.3, 13.1, 13.2, 13.3_

- [ ]* 8.1 Write property test for custom context inclusion
  - **Feature: readme-generator, Property 9: Custom Context Inclusion**
  - **Validates: Requirements 6.3, 13.2**

- [ ]* 8.2 Write property test for special character handling
  - **Feature: readme-generator, Property 16: Special Character Handling**
  - **Validates: Requirements 13.3**

## Phase 5: Installation and Usage Instructions

- [ ] 9. Implement language-specific installation instructions
  - Generate npm install for Node.js projects
  - Generate venv and pip install for Python projects
  - Generate Maven build instructions for Java projects
  - _Requirements: 7.1, 7.2, 7.3_

- [ ]* 9.1 Write property test for installation instructions
  - **Feature: readme-generator, Property 10: Installation Instructions Language-Specific**
  - **Validates: Requirements 7.1, 7.2, 7.3**

- [ ] 10. Implement language-specific usage instructions
  - Generate npm start or node commands for Node.js
  - Generate uvicorn commands for Python FastAPI projects
  - Generate python commands for generic Python projects
  - _Requirements: 8.1, 8.2, 8.3_

- [ ]* 10.1 Write property test for usage instructions
  - **Feature: readme-generator, Property 11: Usage Instructions Accuracy**
  - **Validates: Requirements 8.1, 8.2, 8.3**

## Phase 6: File I/O and Error Handling

- [ ] 11. Implement file I/O operations
  - Implement save functionality for local directories
  - Implement remote path rejection logic
  - Add directory existence validation
  - _Requirements: 9.1, 9.2, 9.3_

- [ ]* 11.1 Write property test for file I/O operations
  - **Feature: readme-generator, Property 12: File I/O Operations**
  - **Validates: Requirements 9.1, 9.2, 9.3**

- [ ] 12. Implement comprehensive error handling
  - Add empty path validation
  - Implement Git clone error handling
  - Add file read error handling with continuation
  - Implement resource cleanup on errors
  - _Requirements: 10.1, 10.2, 10.3_

- [ ]* 12.1 Write property test for error handling
  - **Feature: readme-generator, Property 13: Error Handling Robustness**
  - **Validates: Requirements 10.1, 10.2, 10.3**

## Phase 7: Project Structure and Metadata

- [ ] 13. Implement project structure tree generation
  - Create tree view builder with proper formatting
  - Implement ignored directory filtering
  - Implement depth limiting to 4 levels
  - _Requirements: 11.1, 11.2, 11.3_

- [ ]* 13.1 Write property test for project structure tree
  - **Feature: readme-generator, Property 14: Project Structure Tree Depth**
  - **Validates: Requirements 11.1, 11.2, 11.3**

- [ ] 14. Implement license detection
  - Create LICENSE file reader
  - Implement license type identification (MIT, Apache, GPL)
  - Add default "Unlicensed" fallback
  - _Requirements: 12.1, 12.2, 12.3_

- [ ]* 14.1 Write property test for license detection
  - **Feature: readme-generator, Property 15: License Detection**
  - **Validates: Requirements 12.1, 12.2, 12.3**

## Phase 8: GitHub Metadata and Parser Round-Trip

- [ ] 15. Implement GitHub repository metadata extraction
  - Extract repository URL from Git config
  - Parse username and repository name from URL
  - Implement fallback to language badges
  - _Requirements: 14.1, 14.2, 14.3_

- [ ]* 15.1 Write property test for GitHub metadata extraction
  - **Feature: readme-generator, Property 17: GitHub Metadata Extraction**
  - **Validates: Requirements 14.1, 14.2, 14.3**

- [ ] 16. Implement parser round-trip validation
  - Create JSON parser with serialization
  - Create requirements.txt parser with serialization
  - Ensure data preservation during round-trip
  - _Requirements: 15.1, 15.2, 15.3_

- [ ]* 16.1 Write property test for parser round-trip consistency
  - **Feature: readme-generator, Property 18: Parser Round-Trip Consistency**
  - **Validates: Requirements 15.1, 15.2, 15.3**

## Phase 9: Integration and Validation

- [ ] 17. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 17.1 Write integration tests
  - Test end-to-end scanning of sample projects
  - Test README generation for multiple project types
  - Test file save and load operations

- [ ] 18. Integrate all components into DeepScanner
  - Wire together language detection, dependency extraction, entry point detection
  - Integrate architecture diagram generation
  - Integrate template generation with all metadata
  - Integrate error handling throughout
  - _Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1, 11.1, 12.1, 14.1, 15.1_

- [ ] 19. Test API routes
  - Test /generate endpoint with various inputs
  - Test /save endpoint with valid and invalid paths
  - Test error responses and status codes
  - _Requirements: 1.1, 1.2, 1.3, 9.1, 9.3, 10.1, 10.2_

- [ ] 20. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

