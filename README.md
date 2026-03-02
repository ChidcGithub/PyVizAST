# PyVizAST

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-green.svg)
[![GitHub Release (including pre-releases)](https://img.shields.io/github/v/release/chidcGithub/PyVizAST?include_prereleases&label=PyVizAST Latest Version)](https://github.com/chidcGithub/PyVizAST/releases)


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

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Full code analysis |
| `/api/ast` | POST | Get AST graph structure |
| `/api/complexity` | POST | Complexity metrics |
| `/api/performance` | POST | Performance hotspots |
| `/api/security` | POST | Security vulnerabilities |
| `/api/suggestions` | POST | Optimization suggestions |
| `/api/patches` | POST | Generate auto-fix patches |

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

<details> <summary>Version History</summary>

### v0.3.4 (2026-03-02)
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

### v0.3.3 (2026-03-02)
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

### v0.3.2 (2026-03-01)
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

### v0.3.1 (2026-03-01)
**Bug Fixes:**
- Fixed mutable default arguments in Pydantic models (`schemas.py`)
  - Changed `= {}` and `= []` to `Field(default_factory=dict/list)`
  - Prevents shared state between model instances
- Fixed potential `AttributeError` in security scanner (`security.py`)
  - Added `isinstance(node.func, ast.Attribute)` check before accessing `.attr`
- Fixed cyclomatic complexity calculation for elif branches (`complexity.py`)
  - Removed duplicate counting of nested If nodes

**Frontend Memory Leak Fixes:**
- Fixed `requestAnimationFrame` not being cancelled on unmount (`ASTVisualizer.js`)
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

### v0.3.0 (2026-03-01)
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

### v0.2.2 (2026-03-01)
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

### v0.2.1 (2026-03-01)
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
- Rewrote algorithm with multi-dimensional weighted scoring
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

### v0.2.0 (2026-03-01)
- Redesigned UI with monochrome minimalist theme
- Optimized AST visualization for large codebases:
  - Node filtering by priority types
  - Depth limiting for deep trees
  - Auto-simplification for files with >800 nodes
- Fixed Cytoscape rendering issues (style expressions, ResizeObserver errors)
- Fixed Monaco Editor web worker loading
- Added layout algorithm selection (hierarchical, force-directed, breadth-first)
- Added detail level control (overview, normal, detail)

### v0.1.0 (2026-02-28)
- Initial release
- AST parsing and visualization
- Complexity analysis
- Performance hotspot detection
- Security scanning
- Optimization suggestions
- Interactive learning mode
</details>
