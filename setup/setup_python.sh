#!/bin/bash
# Script to set up Python on a self-hosted runner

set -e

echo "Setting up Python for the discussion bot..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected macOS system"
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install Python 3.10
    echo "Installing Python 3.10 via Homebrew..."
    brew install python@3.10
    
    # Add to PATH if needed
    if ! command -v python3 &> /dev/null; then
        echo 'export PATH="/usr/local/opt/python@3.10/bin:$PATH"' >> ~/.zshrc
        echo 'export PATH="/usr/local/opt/python@3.10/bin:$PATH"' >> ~/.bash_profile
        export PATH="/usr/local/opt/python@3.10/bin:$PATH"
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "Detected Linux system"
    
    # Check if we're on a Debian/Ubuntu or RHEL/CentOS system
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        echo "Installing Python 3 via apt..."
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
    elif command -v yum &> /dev/null; then
        # RHEL/CentOS
        echo "Installing Python 3 via yum..."
        sudo yum install -y python3 python3-pip
    else
        echo "Unsupported Linux distribution. Please install Python 3 manually."
        exit 1
    fi
else
    echo "Unsupported operating system: $OSTYPE"
    echo "Please install Python 3.8+ manually."
    exit 1
fi

# Verify Python installation
echo "Verifying Python installation..."
python3 --version
pip3 --version

# Install required packages
echo "Installing required Python packages..."
python3 -m pip install --upgrade pip
python3 -m pip install requests PyGithub python-dotenv rich backoff together

# Get the repository root directory
REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)

# Install project requirements if requirements.txt exists
if [ -f "$REPO_DIR/requirements.txt" ]; then
    echo "Installing project requirements..."
    python3 -m pip install -r "$REPO_DIR/requirements.txt"
fi

echo "Python setup complete!"
echo "You can now run the discussion bot using the GitHub Actions workflow or one of the other methods described in the README." 