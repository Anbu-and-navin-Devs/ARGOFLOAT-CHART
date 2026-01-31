"""
FloatChart - Local Setup Script
One-click setup for running FloatChart locally.

Usage:
    python local_setup.py           # Full setup + launch Data Manager
    python local_setup.py --quick   # Skip to app launch
"""

import os
import sys
import subprocess
import shutil
import webbrowser
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🌊  FloatChart - Local Setup                                ║
║       Ocean Intelligence Platform                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.END}""")

def print_step(step, total, message):
    print(f"\n{Colors.BLUE}[{step}/{total}]{Colors.END} {Colors.BOLD}{message}{Colors.END}")

def print_success(message):
    print(f"  {Colors.GREEN}✓{Colors.END} {message}")

def print_warning(message):
    print(f"  {Colors.WARNING}⚠{Colors.END} {message}")

def print_error(message):
    print(f"  {Colors.FAIL}✗{Colors.END} {message}")

def clean_deployment_files(project_root):
    """
    Remove deployment-specific files after local setup.
    These files are only needed for cloud deployment (Render).
    """
    deployment_files = [
        project_root / "Procfile",
    ]
    
    for file_path in deployment_files:
        if file_path.exists():
            try:
                file_path.unlink()
                print_success(f"Cleaned deployment file: {file_path.name}")
            except Exception:
                pass  # Ignore errors

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_error(f"Python 3.9+ required. You have {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_pip():
    """Check if pip is available."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print_success("pip is available")
        return True
    except:
        print_error("pip not found")
        return False

def create_env_file(project_root):
    """
    Setup environment files for LOCAL development.
    - Creates .env at PROJECT ROOT from .env.example
    - PostgreSQL only (local database)
    """
    root_env = project_root / ".env"
    env_example = project_root / ".env.example"
    
    # Only create root .env if it doesn't exist
    if root_env.exists():
        print_success("Root .env file already exists")
        return True
    
    # Copy .env.example to .env (for local use)
    if env_example.exists():
        shutil.copy(env_example, root_env)
        print_success("Created .env from .env.example")
    else:
        # Fallback: create minimal .env with PostgreSQL
        env_content = """# FloatChart Configuration - Local Setup
# Using PostgreSQL for LOCAL (unlimited storage!)

# 🏠 DATABASE: PostgreSQL
# Install PostgreSQL: https://www.postgresql.org/download/
# Create database: CREATE DATABASE floatchart;
DATABASE_URL=postgresql://postgres:password@localhost:5432/floatchart

# 🧠 AI PROVIDER - Groq (100% FREE!)
# Get FREE key at: https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key_here
"""
        root_env.write_text(env_content)
        print_success("Created .env file at project root")
    
    print_warning("Please edit .env with your PostgreSQL credentials and Groq API key")
    return True

def install_dependencies(project_root):
    """Install Python dependencies."""
    req_file = project_root / "requirements.txt"
    
    if not req_file.exists():
        print_error("requirements.txt not found")
        return False
    
    print("  Installing dependencies (this may take a minute)...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("Dependencies installed successfully")
            return True
        else:
            print_error(f"Installation failed: {result.stderr}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def verify_installation():
    """Verify key packages are installed."""
    packages = ['flask', 'sqlalchemy', 'pandas']
    missing = []
    
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print_warning(f"Some packages may need manual install: {', '.join(missing)}")
        return False
    
    print_success("All key packages verified")
    return True

def check_env_configured(project_root):
    """Check if .env (at project root) has real credentials."""
    env_file = project_root / ".env"
    
    if not env_file.exists():
        return False
    
    content = env_file.read_text()
    
    # Check for placeholder values (user needs to replace these)
    if "your_groq_api_key_here" in content or "your_password" in content:
        return False
    
    return "DATABASE_URL=" in content and len(content) > 50

def launch_data_manager(project_root):
    """Launch the Data Manager web app."""
    data_gen_dir = project_root / "DATA_GENERATOR"
    
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║            🚀 Launching Data Manager                          ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.END}
The Data Manager will open in your browser.
Use it to download ARGO oceanographic data.

{Colors.WARNING}Press Ctrl+C to stop the server when done.{Colors.END}
""")
    
    time.sleep(1)
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:5001")
    
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run the data manager
    os.chdir(data_gen_dir)
    subprocess.run([sys.executable, "app.py"])

def show_quick_launch_menu(project_root):
    """Show menu for quick launch options."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                    FloatChart Ready! 🎉                       ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.END}
{Colors.BOLD}What would you like to do?{Colors.END}

  {Colors.CYAN}1{Colors.END} - Launch Data Manager (download ARGO data)
  {Colors.CYAN}2{Colors.END} - Launch Chat App (requires data)
  {Colors.CYAN}3{Colors.END} - Show setup instructions
  {Colors.CYAN}q{Colors.END} - Quit

""")
    
    while True:
        choice = input(f"{Colors.BOLD}Enter choice (1/2/3/q): {Colors.END}").strip().lower()
        
        if choice == '1':
            launch_data_manager(project_root)
            break
        elif choice == '2':
            launch_chatbot(project_root)
            break
        elif choice == '3':
            show_instructions()
        elif choice == 'q':
            print("\nGoodbye! 🌊")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or q.")

def launch_chatbot(project_root):
    """Launch the Chat App."""
    chatbot_dir = project_root / "ARGO_CHATBOT"
    
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║            🚀 Launching FloatChart Chat                       ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.END}
The Chat App will open in your browser.

{Colors.WARNING}Press Ctrl+C to stop the server when done.{Colors.END}
""")
    
    time.sleep(1)
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:5000")
    
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run the chatbot
    os.chdir(chatbot_dir)
    subprocess.run([sys.executable, "app.py"])

def show_instructions():
    """Show detailed setup instructions."""
    print(f"""
{Colors.BOLD}📝 SETUP INSTRUCTIONS:{Colors.END}

{Colors.CYAN}1. Setup Database (PostgreSQL):{Colors.END}
   • Install PostgreSQL: https://postgresql.org/download
   • Open pgAdmin or psql terminal
   • Create database: CREATE DATABASE floatchart;
   • Note your password for postgres user

{Colors.CYAN}2. Get a FREE AI API Key (Groq):{Colors.END}
   • Go to https://console.groq.com/keys
   • Sign up with Google/GitHub (30 seconds)
   • Create API key - 100% FREE, no limits!

{Colors.CYAN}3. Configure .env:{Colors.END}
   Edit {Colors.BOLD}.env{Colors.END} in project root:
   
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/floatchart
   GROQ_API_KEY=gsk_...

{Colors.CYAN}4. Download Data:{Colors.END}
   Run: cd DATA_GENERATOR && python app.py
   → Opens wizard at http://localhost:5001

{Colors.CYAN}5. Launch Chat App:{Colors.END}
   Run: cd ARGO_CHATBOT && python app.py
   → Opens chat at http://localhost:5000

""")

def main():
    print_banner()
    
    project_root = Path(__file__).parent.absolute()
    
    # Check for --quick flag
    quick_mode = "--quick" in sys.argv
    
    if not quick_mode:
        total_steps = 4
        
        # Step 1: Check Python
        print_step(1, total_steps, "Checking Python version...")
        if not check_python_version():
            sys.exit(1)
        
        # Step 2: Check pip
        print_step(2, total_steps, "Checking pip...")
        if not check_pip():
            sys.exit(1)
        
        # Step 3: Install dependencies
        print_step(3, total_steps, "Installing dependencies...")
        if not install_dependencies(project_root):
            print_warning("Some dependencies may have failed. Try: pip install -r requirements.txt")
        
        # Step 4: Create .env file
        print_step(4, total_steps, "Setting up configuration...")
        create_env_file(project_root)
        
        # Clean deployment files (not needed for local)
        clean_deployment_files(project_root)
        
        # Verify
        verify_installation()
    
    # Check if env is configured
    if check_env_configured(project_root):
        print_success("Configuration detected!")
        show_quick_launch_menu(project_root)
    else:
        print(f"""
{Colors.WARNING}{Colors.BOLD}
⚠️  Configuration Required
{Colors.END}
Please edit {Colors.BOLD}.env{Colors.END} (at project root) with your credentials:

  DATABASE_URL=postgresql://postgres:password@localhost:5432/floatchart
  GROQ_API_KEY=your_groq_api_key

{Colors.CYAN}Get free credentials at:{Colors.END}
  • Database: Install PostgreSQL locally (UNLIMITED storage!)
  • AI API:   https://console.groq.com (100% FREE, no limits!)

After configuring, run this script again or:
  cd DATA_GENERATOR && python app.py  (to download data)
  cd ARGO_CHATBOT && python app.py    (to launch chat)
""")

if __name__ == "__main__":
    main()
