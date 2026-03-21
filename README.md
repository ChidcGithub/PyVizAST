```

 ________  ___    ___ ___      ___ ___  ________  ________  ________  _________   
|\   __  \|\  \  /  /|\  \    /  /|\  \|\_____  \|\   __  \|\   ____\|\___   ___\ 
\ \  \|\  \ \  \/  / | \  \  /  / | \  \\|___/  /\ \  \|\  \ \  \___|\|___ \  \_| 
 \ \   ____\ \    / / \ \  \/  / / \ \  \   /  / /\ \   __  \ \_____  \   \ \  \  
  \ \  \___|\/  /  /   \ \    / /   \ \  \ /  /_/__\ \  \ \  \|____|\  \   \ \  \ 
   \ \__\ __/  / /      \ \__/ /     \ \__\\________\ \__\ \__\____\_\  \   \ \__\
    \|__||\___/ /        \|__|/       \|__|\|_______|\|__|\|__|\_________\   \|__|
         \|___|/                                              \|_________|        

```

# PyVizAST

[![Version](https://img.shields.io/badge/Version-1.0.0--beta-blue.svg)](https://github.com/ChidcGithub/PyVizAST)
[![Python](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/ChidcGithub/PyVizAST)
[![Status](https://img.shields.io/badge/Status-beta-orange.svg)](https://github.com/ChidcGithub/PyVizAST)
![CI Build Status](https://github.com/ChidcGithub/PyVizAST/actions/workflows/ci.yml/badge.svg)

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

### LLM AI Features (v1.0.0-beta)
- **Local LLM Integration**: Powered by Ollama for privacy-first AI features
- **Auto Install Ollama**: One-click automatic Ollama installation and configuration
- **AI Node Explanations**: Get intelligent explanations for any AST node
  - Code context-aware explanations
  - Python documentation snippets
  - Practical code examples
  - Related concepts
  - Fullscreen view for detailed reading
  - Auto-retry on failure (up to 2 times)
- **AI Challenge Generation**: Generate custom coding challenges with LLM
- **AI Hints**: Get contextual hints during challenge solving
- **Model Management**:
  - Recommended models for code analysis (CodeLlama, DeepSeek Coder, etc.)
  - One-click model download with aria2 acceleration
  - Auto-select best model for code analysis
  - Model status monitoring (installed/running)
- **Settings Panel**: Configure LLM features:
  - Enable/disable AI explanations, challenges, hints
  - Temperature and token limits
  - Model selection with "Load" button to enable LLM

### Easter Egg
- Just explore the project and you'll find it :)

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
- Python 3.9+
- Node.js 18+ (optional, for frontend)

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

| Endpoint                    | Method | Description                      |
|-----------------------------|--------|----------------------------------|
| `/api/analyze`              | POST   | Full code analysis               |
| `/api/ast`                  | POST   | Get AST graph structure          |
| `/api/complexity`           | POST   | Complexity metrics               |
| `/api/performance`          | POST   | Performance hotspots             |
| `/api/security`             | POST   | Security vulnerabilities         |
| `/api/suggestions`          | POST   | Optimization suggestions         |
| `/api/patches`              | POST   | Generate auto-fix patches        |
| `/api/apply-patch`          | POST   | Apply a patch to code            |
| `/api/health`               | GET    | Server health check              |
| `/api/project/analyze`      | POST   | Full project analysis (ZIP)      |
| `/api/progress/{task_id}`   | GET    | Get task progress                |
| `/api/progress/{task_id}/stream` | GET | SSE progress stream           |
| `/api/challenges`           | GET    | List code challenges             |
| `/api/challenges/categories`| GET    | Get challenge categories         |
| `/api/challenges/{id}`      | GET    | Get challenge details            |
| `/api/challenges/submit`    | POST   | Submit challenge answer          |
| `/api/learn/node/{node_id}` | POST   | Get AST node explanation         |

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
<summary>v1.0.0-beta (2026-03-21)</summary>

**LLM AI Refactoring & Bug Fixes**

**LLM Explanation Panel Refactoring:**
- Redesigned AI explanation panel with premium black/white minimalist theme
- Added unavailable state UI with helpful messages when LLM not configured
- Added fullscreen modal for detailed reading
- Improved loading states and error handling
- Auto-retry on failure (up to 2 times)

**Backend LLM Service Refactoring:**
- Improved prompt templates with clearer JSON output format requirements
- Multi-strategy JSON parsing with fallback mechanisms
- Thread-safe caching with TTL for explanation caching
- Case-insensitive model name matching (codeLlama:7b vs codellama:7b)
- Separated error handling for availability check and model listing
- Added shorter timeouts to avoid UI hanging

**Frontend LLM Integration Improvements:**
- Added custom event system (`llmConfigChanged`) for cross-component communication
- Fixed React Hooks order issue (useMemo before early return)
- Fixed incorrect default status value (`'ready'` → `'unavailable'`)
- Improved SSE parsing with type annotations
- Better error feedback and loading states

**Files Added:**
- `frontend/src/components/LLMExplanationPanel.js` - AI explanation panel component
- `frontend/src/components/LLMExplanationPanel.css` - Black/white minimalist styles

**Files Modified:**
- `backend/llm/prompts.py` - Improved prompt templates
- `backend/llm/service.py` - Multi-strategy parsing, caching, status handling
- `backend/llm/ollama_client.py` - Shorter timeouts
- `backend/routers/llm.py` - Unified error responses, detailed logging
- `frontend/src/api.js` - SSE parsing, shorter timeouts
- `frontend/src/components/LLMSettings.js` - Event dispatching, improved status handling
- `frontend/src/components/ASTVisualizer.js` - Event listeners, fixed default status
- `frontend/src/components/ASTVisualizer3D.js` - Event listeners, fixed default status
- `frontend/src/components/components.css` - LLM explanation panel styles

**Bug Fixes:**
- Fixed model not loading when clicking Load button
- Fixed UI stuck at loading state (timeout optimization)
- Fixed false "loaded" display when model not actually loaded
- Fixed React Hooks error (useMemo called after early return)
- Fixed model name case sensitivity matching

</details>

<details>
<summary>v1.0.0-alpha (2026-03-16)</summary>

**Major Release - LLM AI Integration**

**New Features:**

**LLM Service Module (`backend/llm/`):**
- `models.py`: Data models for LLM configuration, status, and responses
- `ollama_client.py`: Ollama API client for local LLM communication
- `prompts.py`: Prompt templates for node explanations, challenges, and hints
- `service.py`: Core LLM service with explanation/challenge/hint generation
- `downloader.py`: Ollama auto-install and model download with aria2 acceleration

**LLM API Endpoints (`backend/routers/llm.py`):**
- `GET /api/llm/status` - Get LLM service status
- `GET/POST /api/llm/config` - LLM configuration management
- `GET /api/llm/models` - List installed models
- `POST /api/llm/models/pull` - Download model with progress streaming
- `DELETE /api/llm/models/{name}` - Delete model
- `GET /api/llm/ollama/status` - Get Ollama installation status
- `POST /api/llm/ollama/install` - Auto-install Ollama
- `POST /api/llm/ollama/start` - Start Ollama server
- `POST /api/llm/generate/explanation` - Generate node explanation
- `POST /api/llm/generate/challenge` - Generate coding challenge
- `POST /api/llm/generate/hint` - Generate contextual hint

**Frontend Components:**
- `LLMSettings.js`: Settings panel with model management and configuration
- `LLMDownloader.js`: Quick setup wizard for Ollama installation
- `LLMSettings.css`: Black/white minimalist design styles

**AI Node Explanations (2D & 3D):**
- AI explanations display in node detail panel when LLM is enabled
- Code context snippet shown with explanations
- Fullscreen modal for detailed reading
- Auto-retry on failure (up to 2 times)
- Error display with manual retry button

**Model Management:**
- Recommended models: CodeLlama 7B/13B, Llama 3.2 3B, Mistral 7B, DeepSeek Coder, Qwen 2.5 Coder
- One-click download with progress tracking
- Auto-select best model for code analysis
- "Use" button for installed models, "In Use" indicator for current model

**Ollama Auto-Install:**
- Automatic platform detection (Windows/macOS/Linux)
- One-click Ollama installation
- Automatic server startup
- Status monitoring (installed/running)

**Configuration Options:**
- Enable/disable LLM features
- Toggle AI explanations, challenges, hints separately
- Temperature and max tokens settings
- Model selection with "Load" button

**Bug Fixes:**
- Fixed model name case sensitivity matching (codeLlama:7b vs codellama:7b)
- Fixed async state update issue in Load button
- Fixed LLM explanation status checks
- Fixed pullModel API to use POST with streaming

**Dependencies Added:**
- `httpx>=0.27.0` for LLM API calls

**Files Added:**
- `backend/llm/__init__.py`
- `backend/llm/models.py`
- `backend/llm/ollama_client.py`
- `backend/llm/prompts.py`
- `backend/llm/service.py`
- `backend/llm/downloader.py`
- `backend/routers/llm.py`
- `frontend/src/components/LLMSettings.js`
- `frontend/src/components/LLMDownloader.js`
- `frontend/src/components/LLMSettings.css`

**Files Modified:**
- `backend/config.py` - Version bump
- `backend/main.py` - LLM router registration
- `backend/routers/__init__.py` - Export LLM router
- `backend/routers/learning.py` - LLM-enhanced explanations
- `backend/routers/challenges.py` - LLM challenge generation
- `frontend/src/App.js` - LLM settings modal
- `frontend/src/api.js` - LLM API functions
- `frontend/src/components/Header.js` - AI button
- `frontend/src/components/ASTVisualizer.js` - AI explanations
- `frontend/src/components/ASTVisualizer3D.js` - AI explanations
- `frontend/src/components/components.css` - LLM explanation styles
- `frontend/src/components/LearnChallenge.css` - LLM toggle styles
- `requirements.txt` - Added httpx

</details>

<details>
<summary>v0.7.2 (2026-03-15)</summary>

**Bug Fixes & Security Improvements**

**Python Version Requirement:**
- Updated minimum Python version from 3.8 to 3.9 (required for `ast.unparse()`)

**Security Improvements:**
- Added ZIP compression bomb detection:
  - Maximum uncompressed size limit (500MB)
  - Maximum compression ratio check (100x)
  - Individual file size limit (5MB)
- Simplified error messages to avoid exposing internal implementation details

**Code Quality:**
- Added logging for exceptions in `node_builder.py`
- Added user feedback for keyboard interrupt in `run.py`
- Locked dependency versions in `requirements.txt` (fastapi, pydantic, uvicorn, etc.)
- Added Node.js/npm version requirements in `package.json` (Node.js >= 18, npm >= 9)

**UI Improvements:**
- Refactored Social Card Generator to black/white minimalist design
- Simplified card visual effects with clean geometric AST visualization
- Improved consistency with project's overall monochrome theme

**Verification:**
- Confirmed all Map.get() calls in `ASTVisualizer3D.js` have proper null checks
- Confirmed `ModuleInfo` dataclass has correct default values

**Files Modified:**
- `run.py` - Python version check, keyboard interrupt handling
- `backend/ast_parser/node_builder.py` - Exception logging
- `backend/project_analyzer/scanner.py` - ZIP bomb detection
- `backend/main.py` - Simplified error messages
- `requirements.txt` - Version constraints
- `frontend/package.json` - Node.js version requirements, version bump
- `backend/config.py` - Version bump
- `frontend/src/components/SocialCardGenerator.js` - Refactored to black/white minimalist design
- `frontend/src/App.css` - Updated social card styles to match project theme
- `README.md` - Version badge, Python requirement, changelog

</details>

<details>
<summary>v0.7.1 (2026-03-14)</summary>

**Social Card Generator & UI Improvements**

**New Features:**
- **Social Card Generator**: Generate shareable image cards from the Share dropdown
  - Brand card with AST visualization, logo, and feature highlights
  - 2D Preview card with captured AST visualization
  - 3D Preview card with captured 3D AST visualization
  - Black/white theme adaptation
  - PNG download (1200x630px standard social share size)

**Toast System Improvements:**
- Toast position moved to top-right of screen
- Simplified vertical stacking (removed complex stacking logic)
- Increased maximum toast limit from 5 to 15
- Increased border-radius from 16px to 24px for rounder corners

**UI Enhancements:**
- Share button now shows dropdown menu with "Share Code" and "Social Card" options
- Visualizer components expose `captureScreenshot` method for card generation
- Improved card preview modal with style selector

**Known Issues:**
- Social Card export may be unstable in certain browsers/conditions
- 3D visualization capture requires the 3D view to be fully rendered

**Files Modified:**
- `frontend/src/components/SocialCardGenerator.js` - New social card generator component
- `frontend/src/components/Header.js` - Share dropdown menu
- `frontend/src/components/Toast.js` - Simplified toast system
- `frontend/src/components/ToastContext.js` - Increased toast limit
- `frontend/src/App.js` - Screenshot capture handlers
- `frontend/src/App.css` - Social card styles, toast improvements
- `frontend/src/components/ASTVisualizer.js` - Screenshot capture method
- `frontend/src/components/ASTVisualizer3D.js` - Screenshot capture method

</details>

<details>
<summary>v0.7.0 (2026-03-14)</summary>

**Major Release - Dependencies Upgrade & 3D Gesture Control**

**Dependencies Upgrade:**
- React 18 → React 19.2.4
- @react-three/fiber 8 → 9.5.0
- @react-three/drei 9 → 10.7.7
- framer-motion 11 → 12.36.0
- three 0.160 → 0.183.2
- cytoscape-react 3 → 4.0.0
- All other dependencies updated to latest versions

**3D Gesture Control:**
- Implemented pointing gesture for 3D AST visualization
- Virtual cursor with dot, ring, progress ring, and snap indicator
- 3D-to-screen coordinate projection using Three.js camera
- Node snapping with smooth animation
- Hover progress for auto-selection (800ms dwell time)
- Camera focus on selected nodes

**Virtual Cursor System:**
- Unified state management with `cursorStateRef`
- Smooth position interpolation (0.25 factor for cursor, 0.35 for snap)
- GPU-accelerated transforms for better performance
- Theme-aware CSS variables for cursor colors
- Separate CSS classes for 2D (`cursor-snap`) and 3D (`cursor-snap-3d`)

**Light Mode Fixes:**
- Fixed `.detail-tag.scope` and `.detail-tag.callable` using white transparency
- Fixed `.relationship-tag.inheritance/derived/method` theme compatibility
- Fixed `.highlighted-line` background color
- Fixed `.warning-dismiss:hover` background
- Fixed `@keyframes searchPulse` with theme-aware `--pulse-color` variable

**Bug Fixes:**
- Fixed cursor dot/ring centering (offset calculations: 10px→-5, 44px→-22)
- Fixed CSS animation conflicting with JS transform positioning
- Fixed 3D node projection coordinate system issues
- Fixed container reference binding for correct cursor positioning

**Files Modified:**
- `frontend/package.json` - Dependencies upgrade
- `frontend/src/components/ASTVisualizer3D.js` - 3D gesture control implementation
- `frontend/src/components/components.css` - Cursor styles, light mode fixes
- `frontend/src/App.js` - Gesture handling
- `backend/main.py` - Version bump

</details>

<details>
<summary>v0.7.0-rc3 (2026-03-13)</summary>

**Bug Fixes & Performance Optimizations**

**Backend Fixes:**
- Fixed async sync blocking in `projects.py`: Added `run_in_executor` for file I/O and AST parsing operations
- Fixed incomplete exception handling in `parser.py`: Added `MemoryError` catch with smart truncation
- Fixed redundant AST traversal in `node_builder.py`: Combined 3 separate `ast.walk` calls into single pass for 3x performance improvement
- Fixed lint errors (F541, F821, F401) across multiple files

**Frontend Improvements:**
- Enhanced `CodeEditor.js` for large file performance:
  - Disabled minimap for files > 3000 lines
  - Disabled folding for files > 5000 lines
  - Added performance warning banner for large files
  - Improved memory management for very large files
- Confirmed proper cleanup in `useResizeObserver.js`, `GestureService.js`, and `ASTVisualizer3D.js`

**Performance:**
- `node_builder.py`: `_count_code_elements()` now does single traversal instead of 3
- Reduced memory usage for large file editing
- Better error handling for edge cases

**Files Modified:**
- `backend/routers/projects.py` - Async file operations
- `backend/ast_parser/parser.py` - MemoryError handling
- `backend/ast_parser/node_builder.py` - Performance optimization
- `frontend/src/components/CodeEditor.js` - Large file handling
- `frontend/src/components/components.css` - Performance warning styles

</details>

<details>
<summary>v0.7.0-rc2 (2026-03-13)</summary>

**Virtual Cursor System Rewrite**

**Complete Refactor:**
- Unified state management: Single `cursorStateRef` object instead of multiple states
- Smooth position interpolation with `CURSOR_SMOOTH` and `SNAP_SMOOTH` factors
- CSS variables for theme support (`--cursor-bg`, `--cursor-border`, etc.)
- Cleaner class naming: `cursor-dot`, `cursor-ring`, `cursor-progress`, `cursor-snap`

**Snap Animation:**
- Smooth snap indicator following with separate smooth factor (0.2)
- First snap initializes position immediately to avoid delay
- Snap indicator now correctly follows node center position

**Performance Optimizations:**
- CSS `transform` instead of `left/top` for GPU acceleration
- Use `node.renderedPosition()` for accurate screen coordinates
- `opacity` transitions instead of `display` for smoother animations
- CSS `will-change` for optimized rendering

**Bug Fixes:**
- Fixed CSS animation conflicting with JS position (use margin centering)
- Fixed snap position using `renderedPosition()` instead of manual calculation
- Fixed snap selecting wrong node (distance squared comparison bug)
- Added validation for `renderedPosition()` return values

**Files Modified:**
- `frontend/src/components/ASTVisualizer.js` - Complete cursor system rewrite
- `frontend/src/components/components.css` - CSS variables, simplified animations
- `frontend/src/App.js` - Removed unused GestureType import

</details>

<details>
<summary>v0.7.0-rc1 (2026-03-13)</summary>

**Code Quality & Bug Fixes**

**Logging Improvements:**
- Upgraded debug logs to warning level for error conditions in project analyzer
- `scanner.py`: File read failures now logged at warning level
- `unused_exports.py`: Module analysis failures now logged at warning level
- `cycle_detector.py`: Improved SCC cycle extraction with better error handling

**Frontend Improvements:**
- `ASTVisualizer.js`: Added `removeAllListeners()` before destroy to prevent memory leaks
- Changed debug logs to warning logs for Cytoscape cleanup errors
- `useResizeObserver.js`: Changed console.debug to console.warn for better error visibility

**Files Modified:**
- `backend/project_analyzer/cycle_detector.py` - Improved cycle detection logging
- `backend/project_analyzer/scanner.py` - Upgraded log levels
- `backend/project_analyzer/unused_exports.py` - Upgraded log levels
- `frontend/src/components/ASTVisualizer.js` - Memory leak prevention
- `frontend/src/hooks/useResizeObserver.js` - Improved error handling

</details>

<details>
<summary>v0.7.0-beta2 (2026-03-12)</summary>

**Gesture Control Improvements**

**Stability Enhancements:**
- Added gesture stability filter: requires 5 consecutive frames with same gesture
- Raised confidence threshold from 0.5 to 0.7
- Added 300ms cooldown period between gesture changes
- Fast reset when hand leaves frame (immediate instead of waiting 5 frames)
- Position tracking continues during cooldown for smooth UX

**Simplified Gesture Set (4 core gestures + pinch):**
- **Thumb Up**: Zoom in
- **Thumb Down**: Zoom out
- **Closed Fist**: Pan mode
- **Open Palm**: Reset view
- **Victory (V sign)**: Select node
- **Pointing Up**: Point-to-select with hover progress
- **Two Hands Pinch**: Pinch to zoom

**Point-to-Select Feature:**
- Virtual cursor appears on AST graph when pointing
- Hover over a node for 2 seconds to auto-select
- Progress ring animation shows selection countdown
- X-axis mirrored to match video preview

**Bug Fixes:**
- Fixed undefined GestureType references (POINTING_UP, VICTORY)
- Fixed callback cleanup on component unmount
- Fixed cooldown visual feedback timing

**Files Modified:**
- `frontend/src/utils/GestureService.js` - Stability filtering, cooldown, pointing direction
- `frontend/src/components/GestureControl.js` - Removed unused icons, added pointing callback
- `frontend/src/components/GestureControl.css` - Cooldown styling
- `frontend/src/utils/logger.js` - Browser safety checks
- `frontend/src/components/ASTVisualizer.js` - Pointing cursor, hover detection, progress ring
- `frontend/src/components/components.css` - Pointing cursor styling
- `frontend/src/App.js` - Pointing direction handling
- `backend/analyzers/security.py` - Expanded secret detection (25+ patterns)
- `backend/project_analyzer/scanner.py` - ZIP path validation
- `frontend/public/index.html` - Title updated to "PyVisAST"

</details>

<details>
<summary>v0.7.0-beta (2026-03-11)</summary>

**New Feature: Webcam Gesture Control**

Hand gesture recognition for 2D/3D AST visualization control using MediaPipe.

**Supported Gestures:**
- **Thumb Up**: Zoom in
- **Thumb Down**: Zoom out
- **Closed Fist**: Pan mode (grab and drag)
- **Open Palm**: Quick tap = select, Hold = reset view
- **Pointing Up**: Select node
- **Victory (V sign)**: Rotate mode
- **Two Hands Pinch**: Pinch to zoom, move both hands to pan

**Components:**
- `GestureService.js`: Core gesture recognition service using MediaPipe GestureRecognizer
- `GestureControl.js`: UI component with camera preview, status indicator, gesture guide
- `GestureControl.css`: Styling for gesture control overlay

**Features:**
- Toggle button in header (default OFF)
- Real-time camera preview with gesture overlay
- Status indicator (loading/ready/running/error/stopped)
- Visual gesture guide with action mappings
- Support for both 2D (Cytoscape) and 3D (Three.js) visualizations

**Dependencies:**
- Added `@mediapipe/tasks-vision` for gesture recognition

**Known Issues:**
- Gesture recognition may be unstable in certain lighting conditions
- Future improvements planned: stability filtering, confidence threshold adjustment, gesture cooldown

**Files Added:**
- `frontend/src/utils/GestureService.js`
- `frontend/src/components/GestureControl.js`
- `frontend/src/components/GestureControl.css`

**Files Modified:**
- `frontend/src/components/Header.js` - Added gesture toggle button
- `frontend/src/App.js` - Added gesture state management
- `frontend/src/components/ASTVisualizer.js` - Added gesture handling for 2D
- `frontend/src/components/ASTVisualizer3D.js` - Added gesture handling for 3D
- `frontend/package.json` - Added MediaPipe dependency

</details>

<details>

<summary>v0.6.3 (2026-03-10)</summary>

**Bug Fixes & Security Improvements**

**Bug Fixes:**
- Fixed CI installation failure in GitHub Actions workflow
  - Changed from `pip install git+https://...` to local `pip install -r requirements.txt`
  - Project doesn't have setup.py, so git install was failing

**Security Improvements:**
- Enhanced path traversal detection in security analyzer
  - Added detection for path construction with format strings
  - Added detection for str.join() with path separators
  - Added detection for f-string path construction
  - Improved os.path.join user input validation warnings

**Documentation:**
- Updated Node.js requirement to 18+ (matching CI configuration)

**Files Modified:**
- `.github/workflows/analyze.yml` - Fixed CI installation
- `backend/analyzers/security.py` - Enhanced path traversal checks
- `backend/main.py` - Version bump to 0.6.3
- `frontend/package.json` - Version bump to 0.6.3
- `README.md` - Version badge and changelog update

</details>

<details>

<summary>v0.6.2 (2026-03-10)</summary>

**UX Improvements & Bug Fixes**

**New Features:**
- **Toast Notification System**: Added toast notifications for user feedback
  - Success/error states with appropriate icons
  - Auto-dismiss after 3 seconds
  - Smooth slide-in/fade-out animations
- **Search Loading Indicator**: Added loading spinner during AST node search
  - Debounced search with 200ms delay
  - Visual feedback while searching
- **Format Code Button**: Added code formatting functionality in Monaco Editor
  - One-click code formatting using Monaco's built-in formatter

**Bug Fixes:**
- Fixed API version inconsistency (root endpoint now returns correct version)
- Fixed copy link failure with no user feedback
- Added proper error handling for clipboard operations

**Code Quality:**
- Enhanced user feedback for all operations
- Improved error states and loading indicators

**Files Modified:**
- `backend/main.py` - API version fix
- `frontend/src/App.js` - Toast notification system
- `frontend/src/App.css` - Toast styles
- `frontend/src/components/ASTVisualizer.js` - Search loading state
- `frontend/src/components/components.css` - Search loading styles
- `frontend/src/components/CodeEditor.js` - Format Code functionality

</details>

<details>

<summary>v0.6.1 (2026-03-09)</summary>



**Bug Fixes & Code Quality Improvements**



**Backend Fixes:**

- Fixed custom exception classes: Added `__init__`, `__str__` methods, error codes, and default messages for `AnalysisError`, `CodeParsingError`, `CodeTooLargeError`, `ResourceNotFoundError`

- Fixed `_parse_patch_hunks` line index counter initialization issue in `patches.py`

- Enhanced `_notify_listeners` error handling in `progress.py` - replaced `pass` with proper error logging

- Improved exception handling in `performance.py` - added logging for caught exceptions



**Frontend Fixes:**

- Fixed `CodeEditor` not supporting `readOnly` prop - Monaco Editor now properly receives the `readOnly` option

- Unified logging system: Replaced all `console.log/error/warn` with structured `logger` utility

- Files updated: `api.js`, `PatchPanel.js`, `ChallengeView.js`, `LearnView.js`, `AnalysisPanel.js`, `ProjectAnalysisView.js`, `ProjectVisualization.js`, `ASTVisualizer.js`, `ASTVisualizer3D.js`, `ErrorBoundary.js`, `App.js`



**Code Quality:**

- 36 console statements replaced with structured logging

- Frontend errors now batch-sent to backend for persistence

- Better error filtering (ignoring ResizeObserver benign errors)

- Development/production environment logging support



**Files Modified:**

- `backend/main.py` - Exception class implementations

- `backend/optimizers/patches.py` - Line index counter fix

- `backend/utils/progress.py` - Error logging

- `backend/analyzers/performance.py` - Exception logging

- `frontend/src/components/CodeEditor.js` - readOnly prop support

- `frontend/src/components/*.js` - Logger integration



</details>



<details>

<summary>v0.6.0 (2026-03-09)</summary>

**Enhanced Backend Code Relationship Analysis & Frontend Sync**

**Backend Enhancements:**
- Add class inheritance analysis (`base_classes`, `derived_classes`, `inheritance_depth`)
- Add method relationship tracking (`methods`, `inherited_methods`, `overridden_methods`)
- Add decorator relationships (`decorators`, `decorated_by`, `decorates`)
- Enhance function call relationships (`calls_to`, `called_by`)
- Add scope nesting tracking (`nested_scopes`, `enclosing_scope_id`, `scope_level`)
- Add variable definition/use tracking (`variables_defined`, `variables_used`)
- Add code pattern statistics (`branch_count`, `loop_count`, `exception_handlers`)
- Add code relationship types (`CodeRelationship`)

**Frontend Synchronization:**
- `ASTVisualizer.js` displays new relationship information
- `components.css` adds relationship label styles (inheritance, decorator, call, pattern, etc.)
- Supports displaying inheritance relationships, decorators, call relationships, code patterns, etc.

</details>

<details>
<summary>v0.5.1 (2026-03-08)</summary>

**UI/UX Improvements:**
- Premium card design with micro-texture effects:
  - Subtle radial gradients and top light strips
  - KPI cards with large primary values (32px/700 weight)
  - Secondary info dimmed with `text-muted` color
  - Status color borders (success/warning/error indicators)
- Enhanced table styling with zebra striping
- Refined button system with gradient backgrounds and hover effects
- Improved shadow and border consistency across all components

**Error Handling Overhaul:**
- Backend returns detailed, user-friendly error messages:
  - Error type classification (TypeError, AttributeError, etc.)
  - Specific suggestions for common issues
  - Recursion/Memory error handling with clear guidance
- Frontend displays structured error panels:
  - Error icon, title, and detailed message
  - Helpful tips for resolution
- AST parser robustness:
  - Graceful handling of unexpected node types
  - Fallback nodes for unparseable structures
  - None value filtering in all `.join()` operations

**Bug Fixes:**
- Fixed `TypeError: sequence item 0: expected str instance, NoneType found`
- Fixed all `.join()` operations to filter None values
- Fixed node creation errors causing analysis crashes
- Fixed ESLint warnings in frontend components

**Files Updated:**
- `AnalysisPanel.css`, `components.css`, `App.css` - UI polish
- `ProjectAnalysisView.css`, `LearnChallenge.css` - Layout refinements
- `parser.py` - Error handling and None filtering
- `main.py` - Enhanced exception handlers
- `api.js`, `App.js` - Frontend error display

</details>

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