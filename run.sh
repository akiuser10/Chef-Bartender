#!/bin/bash
# Bar & Bartender - Development Server Script
# Activates virtual environment and runs Flask development server
cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Clean up corrupted package distributions
echo "Cleaning up package cache..."
pip cache purge 2>/dev/null || true
# Fix corrupted distributions by reinstalling pip
python -m pip install --upgrade --force-reinstall pip 2>/dev/null || true

# Install/update requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -q --upgrade pip
    
    # Packages that may fail to build from source on some systems
    # These are optional for local development
    OPTIONAL_PACKAGES=("psycopg2-binary" "PyMuPDF")
    
    # Create a temporary requirements file excluding optional packages that may fail
    TEMP_REQUIREMENTS="/tmp/requirements_temp_$$.txt"
    cp requirements.txt "$TEMP_REQUIREMENTS"
    
    # Remove optional packages that might fail
    SKIP_PACKAGES=()
    
    # Check for PostgreSQL (psycopg2-binary requires pg_config)
    if ! command -v pg_config &> /dev/null; then
        echo "⚠ PostgreSQL libraries not found (pg_config missing)"
        echo "  Skipping psycopg2-binary (okay for SQLite local dev)"
        echo "  To enable PostgreSQL support, run: brew install libpq"
        grep -v "^psycopg2-binary" "$TEMP_REQUIREMENTS" > "${TEMP_REQUIREMENTS}.new"
        mv "${TEMP_REQUIREMENTS}.new" "$TEMP_REQUIREMENTS"
        SKIP_PACKAGES+=("psycopg2-binary")
    fi
    
    # Try to install PyMuPDF - it may fail with spaces in path or Python 3.14 compatibility
    # PyMuPDF is used for PDF thumbnail generation (optional feature)
    if ! pip install -q "PyMuPDF==1.24.0" 2>/dev/null; then
        echo "⚠ PyMuPDF installation failed (may be due to spaces in path or Python 3.14 compatibility)"
        echo "  PDF thumbnails won't work, but the app will run fine"
        echo "  To install manually: pip install PyMuPDF==1.24.0"
        grep -v "^PyMuPDF" "$TEMP_REQUIREMENTS" > "${TEMP_REQUIREMENTS}.new"
        mv "${TEMP_REQUIREMENTS}.new" "$TEMP_REQUIREMENTS"
        SKIP_PACKAGES+=("PyMuPDF")
    else
        echo "✓ PyMuPDF installed successfully"
    fi
    
    # Install the remaining packages
    echo "Installing core dependencies..."
    if pip install -q -r "$TEMP_REQUIREMENTS"; then
        echo "✓ Core dependencies installed successfully"
    else
        echo "⚠ Some packages failed to install"
        echo "  Trying to install packages one by one..."
        
        # Try installing packages individually to identify which ones fail
        while IFS= read -r package; do
            [ -z "$package" ] && continue
            # Skip comments and empty lines
            [[ "$package" =~ ^[[:space:]]*# ]] && continue
            [[ "$package" =~ ^[[:space:]]*$ ]] && continue
            
            if ! pip install -q "$package" 2>/dev/null; then
                echo "  ⚠ Failed: $package (skipping)"
            fi
        done < "$TEMP_REQUIREMENTS"
    fi
    
    rm -f "$TEMP_REQUIREMENTS"
    
    # Summary
    if [ ${#SKIP_PACKAGES[@]} -gt 0 ]; then
        echo ""
        echo "Skipped packages: ${SKIP_PACKAGES[*]}"
        echo "These can be installed manually later if needed for production."
    fi
fi

export FLASK_APP=app.py
export FLASK_ENV=development

# Find an available port starting from 5001
PORT=5001
MAX_ATTEMPTS=10

# Function to check if port is in use (works on macOS and Linux)
check_port() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1
    elif command -v netstat >/dev/null 2>&1; then
        netstat -an | grep -q ":$port.*LISTEN"
    else
        # Fallback: try to bind to the port using Python
        python3 -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', $port)); s.close()" 2>/dev/null
        [ $? -ne 0 ]
    fi
}

while [ $PORT -lt $((5001 + MAX_ATTEMPTS)) ]; do
    if check_port $PORT; then
        echo "Port $PORT is in use, trying next port..."
        PORT=$((PORT + 1))
    else
        break
    fi
done

if [ $PORT -ge $((5001 + MAX_ATTEMPTS)) ]; then
    echo "⚠ Could not find an available port between 5001-$((5001 + MAX_ATTEMPTS - 1))"
    echo "  Please free up a port or modify run.sh to use a different port range"
    exit 1
fi

if [ $PORT -ne 5001 ]; then
    echo "Using port $PORT instead of 5001"
fi

python -m flask run --host=127.0.0.1 --port=$PORT
