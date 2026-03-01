# PyVizAST

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

## Version History

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
