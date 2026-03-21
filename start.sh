#!/bin/bash
echo "========================================"
echo "  PyVizAST - Python AST Visualizer"
echo "========================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python not found. Please install Python 3.8+"
    exit 1
fi

# Run installation and startup
python3 run.py all
