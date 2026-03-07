# PyVizAST

[![Version](https://img.shields.io/badge/Version-0.5.0-blue.svg)](https://github.com/ChidcGithub/PyVizAST)
[![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/ChidcGithub/PyVizAST)
[![Status](https://img.shields.io/badge/Status-stable-brightgreen.svg)](https://github.com/ChidcGithub/PyVizAST)

A Python AST Visualizer & Static Analyzer that transforms code into interactive graphs. Detect complexity, performance bottlenecks, and code smells with actionable refactoring suggestions.

## Features

### Code Parsing & Visualization Engine
- Parse Python source code into Abstract Syntax Tree (AST) using Python's `ast` module
- Map AST nodes to interactive visual elements with distinct colors and shapes
- Multiple layout algorithms: hierarchical (dagre), force-directed (fcose), breadth-first
- Detail level control: overview, normal, and detail modes for large codebases
- Auto-simplification for files with many nodes to prevent performance issues
- Zoom, pan, and click-to-inspect node details

### Intelligent Analysis Layer
- **Complexity Analysis**: Cyclomatic complexity, cognitive complexity, maintainability index, Halstead metrics
- **Performance Hotspot Detection**: Nested loops, recursion depth, inefficient dictionary/list operations
- **Code Smell Detection**: Long functions, god classes, duplicate code blocks, deep nesting
- **Security Scanning**: SQL injection risks, unsafe deserialization, hardcoded secrets, dangerous function calls

### Optimization Suggestion Engine
- Rule-based refactoring suggestions with specific recommendations
- Auto-fix capability for certain issues (generates unified diff patches)
- Before/after code comparison with estimated performance improvement

### Interactive Learning Mode
- **Code Anatomy**: Highlight execution flow of specific algorithms
- **Beginner Mode**: Display Python documentation when hovering over AST nodes
- **Challenge Mode**: Identify performance issues in provided code samples

### Easter Egg
- Click the "PV" logo 5 times within 2 seconds to discover a hidden surprise
- Features a physics-based confetti animation with 300 realistic paper particles
- Particles spray from screen corners with natural flutter, bend, and fold effects

## Architecture

```
PyVizAST/
├── backend/                 # FastAPI backend
│   ├── ast_parser/         # AST parsing and visualization mapping
│   ├── analyzers/          # Complexity, performance, security analyzers
│   ├── optimizers/         # Suggestion engine and patch generator
│   └── models/             # Pydantic data models
├── frontend/               # React frontend
│   └── src/
│       ├── components/     # UI components
│       └── api.js          # API client
└── requirements.txt        # Python dependencies
```

## Technology Stack

**Backend:**
- FastAPI
- Python `ast` module
- radon (complexity analysis)

**Frontend:**
- React 18
- Cytoscape.js (graph visualization)
- Monaco Editor (code editor)

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+ (optional, for frontend)

### Quick Start

**Windows:**
```batch
start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

**PowerShell:**
```powershell
.\start.ps1
```

**Manual Installation:**
```bash
# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies (optional)
cd frontend && npm install

# Start backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Start frontend (in another terminal)
cd frontend && npm start
```

## Usage

1. Open `http://localhost:3000` in your browser
2. Enter or paste Python code in the editor
3. Click "Analyze" to parse and visualize
4. Explore the AST graph and analysis results

## API Documentation

Access the interactive API documentation at `http://localhost:8000/docs`

### Key Endpoints

| Endpoint           | Method | Description               |
|--------------------|--------|---------------------------|
| `/api/analyze`     | POST   | Full code analysis        |
| `/api/ast`         | POST   | Get AST graph structure   |
| `/api/complexity`  | POST   | Complexity metrics        |
| `/api/performance` | POST   | Performance hotspots      |
| `/api/security`    | POST   | Security vulnerabilities  |
| `/api/suggestions` | POST   | Optimization suggestions  |
| `/api/patches`     | POST   | Generate auto-fix patches |

## Example Analysis

```python
# Sample code with performance issues
def find_duplicates(arr):
    duplicates = []
    for i in range(len(arr)):
        for j in range(len(arr)):
            if i != j and arr[i] == arr[j]:
                if arr[i] not in duplicates:  # O(n) lookup
                    duplicates.append(arr[i])
    return duplicates
```

**Detected Issues:**
- Nested loops: O(n^2) complexity
- List membership check in loop: O(n) per check

**Suggested Fix:**
```python
def find_duplicates(arr):
    seen = set()
    duplicates = set()
    for item in arr:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return list(duplicates)  # O(n) total complexity
```

## Configuration

Analysis thresholds can be configured in `backend/analyzers/`:

- `complexity.py`: Complexity thresholds
- `code_smells.py`: Code smell detection thresholds
- `security.py`: Security check patterns

## Development

```bash
# Run backend in development mode
uvicorn backend.main:app --reload

# Run frontend in development mode
cd frontend && npm start
```

## License

GNU General Public License v3.0

## Contributing

Contributions are welcome. Please submit pull requests to the main repository.

---

<details>

<summary>Version History</summary>

<details>
<summary>v0.5.0 (2026-03-07)</summary>

**Enhanced Node Details:**
- Backend extracts comprehensive node information:
  - Code metrics: line count, character count, indent level
  - Structure info: child count, total descendants, depth, scope name
  - Type annotations: return type, parameter types, default values
  - Function details: local variable count, call count, async/generator flags
  - Class details: method count, attribute count, inheritance info
  - Code patterns: try/except, loop, recursion detection
- Frontend displays all new information in organized sections

**Detail Panel Improvements:**
- Expandable panel with enlarge/collapse buttons
- Close button to dismiss panel
- Expanded mode shows more comfortable spacing and larger fonts
- Clickable tags for navigation:
  - "children" tag navigates to first child node
  - "in [scope]" tag navigates to parent scope
  - Function calls in "Calls" section navigate to corresponding nodes

**3D Layout Options:**
- **Tree Layout**: Clean hierarchical tree structure (default)
- **Grouped Layout**: Nodes grouped by scope in circular arrangements
- **Force Layout**: Optimized force-directed algorithm with level constraints
- New "Minimal" detail level: shows only functions and classes

**Bug Fixes:**
- Fixed detail panel not un-dimming when clicking search result
- Fixed search result hover state not cleared on search close

**Backend Optimizations:**
- Improved AST parsing with more attribute extraction
- Enhanced node mapper to include all new fields
- Added helper functions for type annotations and code patterns

</details>

<details>
<summary>v0.5.0-pre.2 (2026-03-07)</summary>

**3D Visualization Improvements:**
- Signal particle theme adaptation: white in dark mode, black in light mode
- Node detail panel icon theme adaptation
- Signal edge colors adapt to theme
- Search result hover now dims the node detail panel

**Search Panel UX:**
- When hovering search results, the panel background becomes transparent
- Non-hovered results fade to 20% opacity
- Node detail panel also fades when search result is hovered (JavaScript-based)

**Bug Fixes:**
- Fixed CSS `:has()` selector not working for cross-element opacity control
- Fixed animation `opacity` override issue with `!important`

</details>

<details>
<summary>v0.5.0-pre (2026-03-07)</summary>

**New Features:**
- **Easter Egg**: Hidden surprise!
- **Progress Tracking**: Real-time progress display for large project analysis
  - SSE-based progress streaming with percentage and current stage
  - Shows current file being analyzed and file count progress
  - Loading overlay with animated progress bar
- **Code Sharing**: Share code snippets via URL
  - Base64 encoded code in URL hash parameter
  - One-click copy share link
  - Auto-restore code from URL on page load
- **Theme Switching**: Enhanced dark/light theme toggle
  - Prominent toggle switch in header
  - Theme preference saved to localStorage
  - Moon icon turns black in light mode for visibility
- **Export Reports**: Export analysis results
  - HTML report with styled analysis summary
  - JSON export for raw analysis data

**Backend Improvements:**
- New progress tracking module (`backend/utils/progress.py`)
- SSE endpoint for real-time progress updates (`/api/progress/{task_id}/stream`)
- Enhanced CORS configuration for SSE support
- Thread-safe progress notification system

**Frontend Improvements:**
- Updated `LoadingOverlay` with progress percentage and stage display
- New `shareUrl` state and share dialog in `Header`
- Export dialog with HTML/JSON options
- Enhanced theme toggle with visual feedback

**Bug Fixes:**
- Fixed loading overlay CSS conflicts (removed duplicate pseudo-elements)
- Fixed `eventSource` variable scope in `ProjectAnalysisView`
- Fixed thread safety in progress notification system
- Fixed progress generator waiting for task creation

</details>

<details>
<summary>v0.4.4 (2026-03-06)</summary>

**Frontend UI Redesign:**
- Premium black & white theme with refined color palette
- Updated 6 CSS files with cohesive design system
- Consistent CSS variables for maintainability
- Smooth transitions and subtle animations

**Search Panel Improvements:**
- Transparent hover effect: When hovering a search result, the panel background and other results become transparent (20% opacity)
- The hovered result remains fully visible for clarity
- Users can now see AST nodes behind the search panel

**Backend Bug Fixes:**
- Fixed unused `_cognitive_visitor` method in `complexity.py` (removed duplicate code)
- Fixed nested loop detection in `patches.py` (loop indent stack tracking)
- Improved hardcoded secret detection in `security.py` (reduced false positives/negatives)
- Added smart truncation for large files in `main.py` (statement boundary detection)
- Added generator expression warning in `suggestions.py` (one-time iteration caution)
- Simplified cycle detection algorithm in `cycle_detector.py` (leveraging Tarjan SCC)

</details>

<details>
<summary>v0.4.2 (2026-03-05)</summary>

**Security Fixes:**
- Fixed ZIP path traversal vulnerability in project scanner - malicious ZIP files can no longer overwrite system files
- Added path validation before extracting ZIP entries

**Bug Fixes:**
- Fixed silent exception handling in `main.py` - MemoryError now properly logged
- Fixed bare `except:` statements in `performance.py` - now uses specific exception types
- Fixed exception handling in `unused_exports.py` - added debug logging
- Fixed exception handling in `patches.py` - added debug logging for f-string conversion
- Fixed exception handling in `scanner.py` - file read errors now logged

**Improvements:**
- Enhanced JSON parse error logging with line and column numbers
- Expanded AST attribute key mapping (12 → 50+ mappings) for better visualization labels
- Improved error messages throughout the codebase

</details>

<details>
<summary>v0.4.1 (2026-03-04)</summary>

**Fixed issues:**
- Fixed the issue where the front-end web page could not start correctly
- Updated translations.

</details>

<details>
<summary>v0.4.0 (2026-03-04)</summary>

**Major Release - Project Analysis & Interactive Learning**

This release includes all features and fixes from alpha, beta, and pre releases.

**New Features:**
- **Project-Level Analysis**: Analyze entire Python projects with dependency tracking
  - Multi-file analysis with dependency graph visualization
  - Circular dependency detection (Tarjan's algorithm)
  - Unused export detection (functions, classes, variables)
  - Project metrics (LOC, file count, average complexity)
- **Learn Mode**: Interactive AST learning with node explanations
  - Write code and visualize AST in real-time
  - Click on nodes to see detailed explanations
  - Python documentation and code examples for each node type
- **Challenges Mode**: Interactive coding challenges
  - 12 professional challenges across 5 categories
  - Difficulty levels: Easy, Medium, Hard
  - Learning objectives and hints
- **Python 3.10+ Support**: `match-case` statement support (NodeType.MATCH)

**Bug Fixes:**
- Fixed temporary directory cleanup timing (data loss issue)
- Fixed boolean detection in performance analyzer (nested ternary)
- Fixed string concatenation patch generator (loop tracking)
- Fixed memory leak in AST visualizer (animation frame cleanup)
- Fixed retry logic overriding user cancellation
- Fixed hardcoded secret false positives
- Fixed type inconsistency in CodeIssue construction
- Fixed dead code detection for raise statements and async functions
- Fixed relative import resolution edge cases
- Fixed particle ID generation conflicts
- Fixed indent stack management in patch generator

**Improvements:**
- Relaxed CodeIssue.type validation with logging
- Removed setup.py from default ignore patterns
- Improved hardcoded secret detection patterns
- Better error messages for validation errors
- Comprehensive logging system (frontend/backend)

</details>

<details>
<summary>v0.4.0-beta3 (2026-03-04)</summary>

**New Features:**
- **Learn Mode**: Interactive AST learning with node explanations
  - Write code and visualize AST in real-time
  - Click on nodes to see detailed explanations
  - Python documentation and code examples for each node type
  - Related concepts for deeper learning
- **Challenges Mode**: Interactive coding challenges
  - 12 professional challenges across 5 categories (Performance, Security, Complexity, Code Smell, Best Practice)
  - Difficulty levels: Easy, Medium, Hard
  - Learning objectives and hints for each challenge
  - Score system with immediate feedback

**Backend Improvements:**
- Enhanced node explanation system with 20+ AST node types
- New `/api/challenges/categories` endpoint for challenge categories
- Auto-reload challenge data when JSON file changes
- Improved challenge scoring and feedback system

**Frontend Improvements:**
- New `LearnView` component with two-panel layout (Code Editor + AST/Explanation)
- New `ChallengeView` component with challenge list, detail, and result views
- Monochrome black/white theme for Learn and Challenges modes
- Responsive layout for different screen sizes
- Integrated Learn/Challenges into Sidebar tabs

**Content:**
- All content translated to English for consistency
- Professional challenge descriptions and learning objectives

</details>

<details>
<summary>v0.4.0-beta2 (2026-03-04)</summary>

**Bug Fixes:**
- Fixed `PerformanceAnalyzer` missing `hotspots` attribute causing validation errors
- Fixed `main.py` incorrectly assigning `issues` to `performance_hotspots` in single-file analysis
- Fixed duplicate imports in `main.py` (removed redundant `pydantic`, `datetime`, `typing` imports)
- Fixed project analysis performance hotspots not displaying in frontend
- Restored `ASTVisualizer3D.js` from git to fix encoding issues

**Code Quality Improvements:**
- Completed empty `pass` implementations in `performance.py`:
  - `_check_loop_contents()`: Now detects repeated `len()` calls and `range(len())` patterns
  - `_detect_inefficient_data_structures()`: Detects list membership checks and `count()` in loops
  - `_detect_redundant_calculations()`: Detects duplicate function calls and operations in loops
  - `_detect_memory_issues()`: Detects potentially large list comprehensions
  - `_detect_unoptimized_comprehensions()`: Context-aware generator expression suggestions
- Completed recursive call detection in `complexity.py` cognitive complexity calculation
- Fixed `patches.py` f-string conversion for complex expressions with attribute access
- Added `PerformanceHotspot` model support with proper `hotspots` list in analyzer

**Performance Detection Enhancements:**
- Nested loop detection now generates both issues and hotspots
- String concatenation in loops now generates performance hotspots
- Big O complexity estimation for detected issues

</details>

<details>
<summary>v0.4.0-beta (2026-03-03)</summary>

**Project-Level Analysis:**
- **Multi-file Analysis**: Analyze entire Python projects with dependency tracking
- **Dependency Graph**: Visualize module imports and relationships
- **Circular Dependency Detection**: Identify and highlight circular imports
- **Unused Export Detection**: Find unused functions and classes
- **Project Metrics**: Lines of code, file count, average complexity

**New Backend Module:**
- `backend/project_analyzer/` - Complete project analysis system
  - `scanner.py` - File discovery and parsing
  - `dependency.py` - Import dependency graph construction
  - `cycle_detector.py` - Circular dependency detection (Tarjan's algorithm)
  - `symbol_extractor.py` - Function/class definition extraction
  - `unused_exports.py` - Unused export detection
  - `metrics.py` - Project-level metrics calculation
  - `models.py` - Data models for project analysis

**Frontend Improvements:**
- New `ProjectAnalysisView` component for file list and project overview
- Enhanced `ProjectVisualization` with dependency graph rendering
- Improved graph visual design with black/white/gray color scheme
- Different node shapes (rectangles, diamonds) and line styles (solid, dashed)
- File double-click to enter edit mode with exit button
- Editor now loads actual file content in project mode
- Auto-open browser on backend startup

**Bug Fixes:**
- Fixed project analysis data format mismatch (module names vs file paths)
- Fixed missing CSS styles for dependency graph visualization
- Fixed AnalysisPanel data aggregation for project mode
- Fixed editor showing sample code instead of actual file content

**API Additions:**
- `POST /api/project/analyze` - Analyze entire project
- `POST /api/project/file` - Analyze single file in project context

</details>

<details>
<summary>v0.4.0-alpha3 (2026-03-03)</summary>

**Bug Fixes:**
- Fixed infinite loop in `main.py` when encountering SyntaxError during memory optimization
- Fixed CSRF detection logic in `security.py` (condition was always true)
- Fixed default value issue in `node_mapper.py` for missing edge nodes
- Fixed global variable leak in `ASTVisualizer.js` (replaced `window.__particleCleanup` with `useRef`)
- Fixed memory leak in particle animation (particle ID collision causing accumulation)
- Fixed Monaco Editor not loading on first page visit
- Fixed ResizeObserver loop errors causing page stretch

**New Features:**
- **Logging System**: Comprehensive frontend and backend logging
  - Backend logs saved to `logs/pyvizast-YYYY-MM-DD.log`
  - Frontend errors captured and sent to backend (`logs/frontend-YYYY-MM-DD.log`)
  - Batched log sending with beacon API for reliability
- **useResizeObserver Hook**: Safe ResizeObserver wrapper
  - Automatic debounce and requestAnimationFrame
  - Proper cleanup on unmount
  - Error suppression for ResizeObserver loop issues

**Optimizations:**
- Disabled Monaco Editor's internal ResizeObserver (uses custom hook instead)
- Added Chinese CDN mirrors for font loading (fonts.font.im, fonts.loli.net)
- Unified ResizeObserver management across all components
- Global ResizeObserver error suppression for development environment

**Code Quality:**
- Removed duplicate `import json` in main.py
- Improved error handling in security scanner
- Added CSS variables for font system

</details>

<details>
<summary>v0.3.4 (2026-03-02)</summary>

**Bug Fixes:**
- Fixed 422 validation error showing `[object Object]` instead of readable message
  - Added `extractErrorMessage` function to properly parse Pydantic validation errors
  - Correctly extracts error details from arrays/objects to display meaningful messages
- Fixed large file support:
  - Increased `MAX_CODE_LENGTH` from 100,000 to 5,000,000 characters
  - Now supports analyzing large project files

**Backend Bug Fixes:**
- Fixed potential infinite recursion in `performance.py` (removed duplicate `generic_visit`)
- Fixed incomplete dead code detection in `code_smells.py` (removed premature `break`)
- Fixed patch parsing logic in `patches.py` (line number tracking)
- Fixed regex false positives in `security.py` (excluded comments and placeholders)
- Added progressive simplification strategy for large files in `main.py`
- Added deduplication in `suggestions.py` to prevent duplicate suggestions

**Frontend Bug Fixes:**
- Fixed memory leak in `ASTVisualizer.js` (animation cancellation flags)
- Fixed useFrame state updates in `ASTVisualizer3D.js` (throttling + ref-based vectors)
- Fixed retry logic in `api.js` (only retry idempotent methods like GET)
- Fixed patch application in `PatchPanel.js` (API-first with fallback)

**Performance Notes:**
- Very large files (millions of characters) may cause:
  - Increased memory usage during AST parsing
  - Performance slowdown in visualization with many nodes
  - Consider splitting large projects into separate files for analysis

</details>

<details>
<summary>v0.3.3 (2026-03-02)</summary>

**New Features:**
- **Search Functionality**: Search nodes in 2D/3D AST view
  - Search by function name, variable name, or node type
  - Keyboard navigation (↑↓ to navigate, Enter to jump, Esc to close)
  - Click search result to focus node and jump to editor line
- **Resizable Panels**: Drag the divider between editor and visualization panels
  - Adjust panel sizes by dragging the center divider
  - Position saved during session (20%-80% range)
  - Responsive design: auto-stacks on smaller screens

**Backend Code Quality:**
- Added input validation in `schemas.py` (code length, line number ranges, type whitelists)
- Added custom exception classes for better error handling
- Refactored exception handling in `main.py` with specific exception types
- Improved production error messages (no stack trace exposure)

**Frontend Bug Fixes:**
- Fixed AST visualizer initialization issue (first analyze not showing graph)
- Fixed 2D/3D switch requiring re-analyze
- Fixed particle key generation strategy to prevent conflicts
- Fixed `useFrame` state update causing potential infinite loops
- Fixed keyboard navigation conflict with search input
- Added `withRetry` wrapper to all API calls for better reliability
- Improved optional chaining consistency in `AnalysisPanel.js`
- Enhanced diff parsing in `PatchPanel.js` with better edge case handling

</details>

<details>
<summary>v0.3.2 (2026-03-01)</summary>

**Animation Redesign:**
- Redesigned particle animations with clean white theme
- Simplified particle rendering for better performance
- Unified animation loop for camera movements

**Performance Optimizations:**
- Reduced sphere geometry segments (16→8) for 75% fewer vertices
- Removed redundant Line component from SignalParticle
- Single glow mesh instead of multiple layers
- Removed unnecessary useFrame rotation animation
- Simplified SVG particle: single circle instead of two
- Reduced blur filter intensity for faster rendering

**Code Quality:**
- Unified camera animations into single `useFrame` loop
- Removed duplicate `requestAnimationFrame` loop in resetCamera
- Cleaner code with 49 fewer lines

**Bug Fixes:**
- Fixed signal propagation animation not playing (removed `isMountedRef` checks)
- Fixed animation conflicts between reset and keyboard/focus animations

</details>

<details>
<summary>v0.3.1 (2026-03-01)</summary>

**Bug Fixes:**
- Fixed mutable default arguments in Pydantic models (`schemas.py`)
  - Changed `= {}` and `= []` to `Field(default_factory=dict/list)`
  - Prevents shared state between model instances
- Fixed potential `AttributeError` in security scanner (`security.py`)
  - Added `isinstance(node.func, ast.Attribute)` check before accessing `.attr`
- Fixed cyclomatic complexity calculation for elif branches (`complexity.py`)
  - Removed duplicate counting of nested If nodes

**Frontend Memory Leak Fixes:**
- Fixed `requestAnimationFrame` not being canceled on unmount (`ASTVisualizer.js`)
- Fixed `setTimeout` not being cleared on unmount (`ASTVisualizer.js`, `ASTVisualizer3D.js`)
- Added proper cleanup for event listeners and timers
- Added `isMountedRef` to prevent state updates after unmount

**Performance Optimizations:**
- Added `React.memo` to panel components (`AnalysisPanel.js`)
  - `ComplexityPanel`, `PerformancePanel`, `SecurityPanel`, `SuggestionsPanel`
  - `MetricCard`, `DetailItem`, `IssueList`, `SuggestionCard`
- Implemented code splitting with `React.lazy` (`App.js`)
  - Lazy loading for `ASTVisualizer`, `ASTVisualizer3D`, `AnalysisPanel`
  - Added loading fallback component

**Error Handling Improvements:**
- Enhanced `ErrorBoundary` component with error type classification
  - Network errors, syntax errors, runtime errors, chunk load errors
  - Different recovery suggestions based on error type
- Added `LazyLoadErrorBoundary` for lazy-loaded components
- Improved development mode error logging

</details>

<details>
<summary>v0.3.0 (2026-03-01)</summary>

**3D Visualization:**
- Added 3D AST view with Three.js and React Three Fiber
- Custom 3D force-directed layout algorithm for automatic node positioning
- Different 3D shapes for node types (boxes for structures, diamonds for control flow, spheres for expressions)
- OrbitControls for camera manipulation (drag to rotate, scroll to zoom)
- Reset camera button to return to initial view

**Signal Propagation Animation:**
- Long press on a node to focus and display detailed information
- Release to trigger electric-like signal propagation animation
- Particles travel along edges at constant speed (duration based on edge length)
- Target nodes glow with fade-in/fade-out animation when particles approach
- Smooth BFS-based wave propagation (up to 5 levels deep)

**Keyboard Navigation:**
- WASD / Arrow keys for smooth horizontal camera movement
- Space bar to move camera up
- Shift key to move camera down
- Continuous movement while keys are held

**UI Improvements:**
- Server connection status indicator with helpful error messages
- Better error handling and display
- Improved startup error reporting in run.py
- Removed emoji from detail panel labels

**Bug Fixes:**
- Fixed `PatchApplyRequest` undefined error (moved class definition before usage)
- Fixed `__builtins__` type check reliability in performance analyzer
- Fixed particle duplication issue (added edge-level visited tracking)
- Fixed particle position offset issue (positions now fetched at animation time)
- Fixed 3D particle reference issue (positions now copied, not referenced)

</details>

<details>
<summary>v0.2.2 (2026-03-01)</summary>

**New Features:**
- **Patch Application UI**: Interactive interface to preview and apply auto-fix patches
  - Unified diff preview with syntax highlighting
  - One-click patch application to code editor
  - Visual status tracking for applied patches
- **Enhanced AST Node Details**: Richer information for learning
  - Descriptive icons for each node type (ƒ for functions, C for classes, etc.)
  - Detailed labels showing full signatures (e.g., `def func(arg1, arg2)`)
  - Educational explanations for each node type
  - Attribute display (parameters, decorators, base classes, etc.)
- **Patch Context Validation**: Improved safety for auto-fix
  - Validates context lines before applying patches
  - Prevents incorrect modifications to code

**Bug Fixes:**
- Fixed f-string syntax error in parser.py (escape `{}` to `{{}}`)
- Fixed dictionary syntax error in suggestions.py

</details>

<details>
<summary>v0.2.1 (2026-03-01)</summary>

**Bug Fixes:**
- Fixed CORS security configuration - now uses environment variable `ALLOWED_ORIGINS`
- Fixed analyzer state pollution between requests - each request now creates fresh instances
- Fixed `_detect_magic_numbers` crash due to missing parent node tracking
- Fixed `_generate_node_explanation` crash when node.name is None
- Fixed duplicate state clearing in code_smells.py

**Frontend Improvements:**
- Added 30-second request timeout with friendly error messages
- Added request cancellation on component unmount (AbortController)
- Improved error handling for network issues and server errors

**Performance Detection:**
- Completed string concatenation detection in loops
- Completed global variable lookup detection in loops
- Fixed state accumulation in performance analyzer

**Maintainability Index:**
- Rewrote algorithm with multidimensional weighted scoring
- Now handles large codebases correctly (minimum score 20 instead of 0)
- Considers complexity (35%), scale (25%), function quality (25%), Halstead (15%)

**Patch Generator:**
- Added syntax validation before and after patch generation
- Improved string concatenation fix (auto-adds init and join)
- Improved range(len()) fix (replaces arr[i] with item)
- Improved list membership fix (auto-adds set conversion)
- Added automatic `import ast` insertion for eval→literal_eval fix
- Added error tracking with `get_errors()` method

**Suggestion Engine:**
- Smart detection of list comprehension contexts
- Only suggests generator expression when appropriate:
  - As argument to single-pass functions (sum, any, all, max, min, etc.)
  - Direct iteration in for loop
  - NOT for variable assignment (may need multiple access)
  - NOT for return statements

**Code Quality:**
- Added comprehensive logging throughout backend
- Extracted challenge data to JSON file (`backend/data/challenges.json`)
- Added `AnalyzerFactory` for clean instance creation
- Removed hardcoded data from main.py

</details>

<details>
<summary>v0.2.0 (2026-03-01)</summary>

- Redesigned UI with monochrome minimalist theme
- Optimized AST visualization for large codebases:
  - Node filtering by priority types
  - Depth limiting for deep trees
  - Auto-simplification for files with >800 nodes
- Fixed Cytoscape rendering issues (style expressions, ResizeObserver errors)
- Fixed Monaco Editor web worker loading
- Added layout algorithm selection (hierarchical, force-directed, breadth-first)
- Added detail level control (overview, normal, detail)

</details>

<details>
<summary>v0.1.0 (2026-02-28)</summary>

- Initial release
- AST parsing and visualization
- Complexity analysis
- Performance hotspot detection
- Security scanning
- Optimization suggestions
- Interactive learning mode

</details>

</details>