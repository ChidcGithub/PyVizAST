"""
PyVizAST - Python AST Visualizer & Static Analyzer
Startup Script

@author: Chidc
@link: github.com/chidcGithub
"""
import os
import sys
import subprocess
import argparse
import threading
import time
import webbrowser


def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        sys.exit(1)
    print(f"✓ Python version: {sys.version.split()[0]}")


def install_backend_deps():
    """Install backend dependencies"""
    print("\nInstalling backend dependencies...")
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', requirements_path],
            check=True
        )
        print("✓ Backend dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install backend dependencies: {e}")
        sys.exit(1)


def install_frontend_deps():
    """Install frontend dependencies"""
    print("\nInstalling frontend dependencies...")
    frontend_path = os.path.join(os.path.dirname(__file__), 'frontend')
    
    # Check if npm is available
    try:
        subprocess.run(['npm', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ npm not found, please install Node.js first")
        return False
    
    try:
        subprocess.run(['npm', 'install'], cwd=frontend_path, check=True)
        print("✓ Frontend dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install frontend dependencies: {e}")
        return False


def start_backend(host='0.0.0.0', port=8000, open_browser=True):
    """Start backend server"""
    print(f"\nStarting backend server (http://{host}:{port})...")
    
    # Open browser in background thread with delay
    def open_browser_delayed():
        time.sleep(1.5)  # Wait for server to start
        url = f"http://localhost:{port}"
        print(f"\nOpening browser: {url}")
        webbrowser.open(url)
    
    if open_browser:
        browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
        browser_thread.start()
    
    backend_path = os.path.dirname(__file__)
    sys.path.insert(0, backend_path)
    
    try:
        import uvicorn
        from backend.main import app
        
        uvicorn.run(app, host=host, port=port)
    except Exception as e:
        print(f"\n{'='*50}")
        print("✗ Backend startup failed!")
        print(f"{'='*50}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        
        # Print full error traceback
        import traceback
        print(f"\nError traceback:")
        print("-" * 50)
        traceback.print_exc()
        print("-" * 50)
        
        sys.exit(1)


def start_frontend(port=3000):
    """Start frontend server"""
    print(f"\nStarting frontend server (http://localhost:{port})...")
    
    frontend_path = os.path.join(os.path.dirname(__file__), 'frontend')
    
    try:
        subprocess.run(['npm', 'start'], cwd=frontend_path)
    except KeyboardInterrupt:
        print("\nFrontend server stopped")


def main():
    parser = argparse.ArgumentParser(
        description='PyVizAST - Python AST Visualizer & Static Analyzer'
    )
    parser.add_argument(
        'command',
        choices=['install', 'backend', 'frontend', 'start', 'all'],
        help='Command: install=install dependencies, backend=start backend, frontend=start frontend, start=start all, all=install and start'
    )
    parser.add_argument('--host', default='0.0.0.0', help='Backend server address')
    parser.add_argument('--port', type=int, default=8000, help='Backend server port')
    parser.add_argument('--frontend-port', type=int, default=3000, help='Frontend server port')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("  PyVizAST - Python AST Visualizer & Static Analyzer")
    print("=" * 50)
    
    check_python_version()
    
    if args.command == 'install':
        install_backend_deps()
        install_frontend_deps()
        
    elif args.command == 'backend':
        start_backend(args.host, args.port, open_browser=True)
        
    elif args.command == 'frontend':
        start_frontend(args.frontend_port)
        
    elif args.command == 'start':
        # Use multiprocessing on Windows
        import multiprocessing
        
        backend_process = multiprocessing.Process(
            target=start_backend,
            args=(args.host, args.port, True)  # Open browser
        )
        
        backend_process.start()
        
        # Wait for backend to start
        import time
        time.sleep(2)
        
        try:
            start_frontend(args.frontend_port)
        except KeyboardInterrupt:
            print("\n\nStopping servers...")
        finally:
            backend_process.terminate()
            
    elif args.command == 'all':
        install_backend_deps()
        if install_frontend_deps():
            import multiprocessing
            import time
            
            backend_process = multiprocessing.Process(
                target=start_backend,
                args=(args.host, args.port, True)  # Open browser
            )
            
            backend_process.start()
            time.sleep(2)
            
            try:
                start_frontend(args.frontend_port)
            except KeyboardInterrupt:
                print("\n\nStopping servers...")
            finally:
                backend_process.terminate()


if __name__ == '__main__':
    main()