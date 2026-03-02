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

### Project-Level Analysis (v0.4.0+)
- **Multi-File Analysis**: Upload ZIP or scan directories for whole-project analysis
- **Dependency Graph**: Visualize module dependencies and detect circular dependencies
- **Cross-File Issues**: Detect unused exports, duplicate code across files
- **Health Score**: Project-level code quality assessment with actionable insights
- **Incremental Analysis**: SQLite-based persistence for fast re-analysis

## Architecture

```
PyVizAST/
├── backend/                 # FastAPI backend
│   ├── ast_parser/         # AST parsing and visualization mapping
│   ├── analyzers/          # Complexity, performance, security analyzers
│   ├── optimizers/         # Suggestion engine and patch generator
│   ├── models/             # Pydantic data models
│   └── project_analyzer/   # Project-level analysis (v0.4.0+)
│       ├── scanner.py      # ZIP/directory scanning
│       ├── processor.py    # Concurrent file processing
│       ├── dependency.py   # Dependency graph builder
│       ├── cache.py        # AST/dependency caching
│       ├── storage.py      # SQLite persistence
│       ├── cli.py          # Command-line interface
│       └── global_rules/   # Cross-file issue detection
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
- SQLite (incremental analysis cache)

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

### Web Interface
1. Open `http://localhost:3000` in your browser
2. Enter or paste Python code in the editor
3. Click "Analyze" to parse and visualize
4. Explore the AST graph and analysis results

### Project Analysis
1. Switch to "Project Analysis" tab
2. Upload a ZIP file containing Python files
3. Click "Analyze" for full project analysis
4. View summary, file details, dependencies, and cross-file issues

### Command Line (v0.4.0+)
```bash
# Analyze a project directory
python -m backend.project_analyzer.cli /path/to/project

# Output JSON report
python -m backend.project_analyzer.cli /path/to/project --output report.json

# Quick mode (complexity only)
python -m backend.project_analyzer.cli /path/to/project --quick

# With whitelist config
python -m backend.project_analyzer.cli /path/to/project --whitelist whitelist.json
```

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
| `/api/project/upload` | POST | Upload project ZIP for preview |
| `/api/project/analyze` | POST | Full project analysis |

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

### Analysis Thresholds
Configurable in `backend/analyzers/`:
- `complexity.py`: Complexity thresholds
- `code_smells.py`: Code smell detection thresholds
- `security.py`: Security check patterns

### Whitelist Configuration (v0.4.0+)
Create `whitelist.json` for unused export detection:
```json
{
  "symbols": ["main", "setup", "create_app"],
  "file_patterns": ["test_", "_test.py", "conftest.py"],
  "path_patterns": ["tests/", "examples/"]
}
```

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

<details>
<summary>Version History</summary>

### v0.4.0-alpha (2026-03-02)
**Project-Level Analysis:**
- Multi-file project analysis via ZIP upload or directory scanning
- Dependency graph construction with cycle detection
- Cross-file issue detection (unused exports, duplicate code)
- Project health score with grading system (A-F)
- File-by-file complexity and issue breakdown

**Performance Optimizations:**
- AST parsing cache with content-based invalidation
- Dependency graph cache for incremental analysis
- SQLite-based result persistence
- Incremental analysis support (only re-analyze changed files)
- Concurrent file processing with ThreadPoolExecutor

**Accuracy Improvements:**
- `__all__` support for export detection
- Conditional import detection (`try/except ImportError`)
- Dynamic import detection (`importlib.import_module`)
- Whitelist configuration for test files and helper functions
- Better relative import resolution

**New Detection Rules:**
- Oversized modules (>1000 lines)
- Too many public APIs per module
- Circular dependency depth analysis
- Module coupling metrics

**CLI Tool:**
- Command-line interface for CI integration
- JSON report output
- Configurable analysis options
- Exit codes based on issue severity

**Frontend Updates:**
- Project analysis view with upload area
- Tab-based navigation (Summary, Files, Issues, Dependencies)
- File preview before analysis
- Consistent analyze workflow with single-file mode

### v0.3.4 (2026-03-02)
**Bug Fixes:**
- Fixed 422 validation error showing `[object Object]` instead of readable message
- Fixed large file support (increased MAX_CODE_LENGTH to 5,000,000 characters)

**Backend Bug Fixes:**
- Fixed potential infinite recursion in `performance.py`
- Fixed incomplete dead code detection in `code_smells.py`
- Fixed patch parsing logic in `patches.py`
- Fixed regex false positives in `security.py`
- Added progressive simplification strategy for large files
- Added deduplication in `suggestions.py`

**Frontend Bug Fixes:**
- Fixed memory leak in `ASTVisualizer.js`
- Fixed useFrame state updates in `ASTVisualizer3D.js`
- Fixed retry logic in `api.js`
- Fixed patch application in `PatchPanel.js`

### v0.3.3 (2026-03-02)
**New Features:**
- Search functionality in 2D/3D AST view
- Resizable panels with drag support

**Backend Code Quality:**
- Added input validation in `schemas.py`
- Added custom exception classes
- Refactored exception handling in `main.py`

### v0.3.2 (2026-03-01)
**Animation Redesign:**
- Redesigned particle animations with clean white theme
- Simplified particle rendering for better performance

**Performance Optimizations:**
- Reduced sphere geometry segments (75% fewer vertices)
- Removed redundant components
- Single glow mesh instead of multiple layers

### v0.3.1 (2026-03-01)
**Bug Fixes:**
- Fixed mutable default arguments in Pydantic models
- Fixed potential `AttributeError` in security scanner
- Fixed cyclomatic complexity calculation for elif branches

**Frontend Memory Leak Fixes:**
- Fixed `requestAnimationFrame` not being cancelled on unmount
- Fixed `setTimeout` not being cleared on unmount
- Added `React.memo` to panel components
- Implemented code splitting with `React.lazy`

### v0.3.0 (2026-03-01)
**3D Visualization:**
- Added 3D AST view with Three.js and React Three Fiber
- Custom 3D force-directed layout algorithm
- OrbitControls for camera manipulation
- Signal propagation animation on long press

**Keyboard Navigation:**
- WASD/Arrow keys for camera movement
- Space/Shift for vertical movement

### v0.2.2 (2026-03-01)
**New Features:**
- Patch application UI with diff preview
- Enhanced AST node details with educational content

### v0.2.1 (2026-03-01)
**Bug Fixes:**
- Fixed CORS security configuration
- Fixed analyzer state pollution between requests
- Fixed various crashes in analyzers

**Frontend Improvements:**
- Added 30-second request timeout
- Added request cancellation on unmount
- Improved error handling

### v0.2.0 (2026-03-01)
- Redesigned UI with monochrome minimalist theme
- Optimized AST visualization for large codebases
- Added layout algorithm selection
- Added detail level control

### v0.1.0 (2026-02-28)
- Initial release
- AST parsing and visualization
- Complexity analysis
- Performance hotspot detection
- Security scanning
- Optimization suggestions
- Interactive learning mode
</details>