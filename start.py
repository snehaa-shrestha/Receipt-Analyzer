
import os
import sys
import uvicorn

# Get the absolute path to the backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend")

def main():
    print(f"Starting Receipt Analyzer Backend...")
    print(f"Setting working directory to: {backend_dir}")
    
    # Change working directory to backend so that .env and app module are found
    if os.path.exists(backend_dir):
        os.chdir(backend_dir)
        # Add backend dir to python path just in case
        sys.path.insert(0, backend_dir)
    else:
        print(f"Error: Could not find 'backend' directory at {backend_dir}")
        return

    # Run Uvicorn programmatically
    # "app.main:app" refers to backend/app/main.py -> app object
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
