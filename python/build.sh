#!/bin/bash
#
# Build script for Python NFC extension
#
# This script builds the Python C extension that interfaces with the Linux NFC library.
# It handles common build issues and provides helpful error messages.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "nfc_python_wrapper.c" ] || [ ! -f "setup.py" ]; then
    print_error "Please run this script from the python/ directory"
    print_error "Expected files: nfc_python_wrapper.c, setup.py"
    exit 1
fi

print_status "Building Python NFC extension..."

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_status "Using Python version: $PYTHON_VERSION"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 6) else 1)'; then
    print_error "Python 3.6 or later is required"
    exit 1
fi

# Check for Python development headers
print_status "Checking for Python development headers..."
if ! python3 -c 'import distutils.util' 2>/dev/null; then
    print_error "Python development headers not found"
    print_error "Install with: sudo apt install python3-dev (Ubuntu/Debian)"
    print_error "             sudo dnf install python3-devel (Fedora)"
    print_error "             sudo yum install python3-devel (CentOS/RHEL)"
    exit 1
fi

# Check for the main NFC library
print_status "Checking for NFC library..."
LIB_PATHS=(
    "../.libs/libnfc_nci_linux.so"
    "../libnfc_nci_linux.so"
    "/usr/local/lib/libnfc_nci_linux.so"
    "/usr/lib/libnfc_nci_linux.so"
)

LIB_FOUND=false
for lib_path in "${LIB_PATHS[@]}"; do
    if [ -f "$lib_path" ]; then
        print_success "Found NFC library: $lib_path"
        LIB_FOUND=true
        break
    fi
done

if [ "$LIB_FOUND" = false ]; then
    print_error "NFC library not found!"
    print_error "Please build the main library first:"
    print_error "  cd .."
    print_error "  ./autogen.sh"
    print_error "  ./configure"
    print_error "  make"
    exit 1
fi

# Check for required system libraries
print_status "Checking system dependencies..."
MISSING_DEPS=()

if ! ldconfig -p | grep -q libgpiod; then
    MISSING_DEPS+=("libgpiod-dev")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    print_warning "Missing system dependencies: ${MISSING_DEPS[*]}"
    print_warning "Install with: sudo apt install ${MISSING_DEPS[*]}"
    print_warning "Continuing anyway - build may fail..."
fi

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf build/
rm -f nfc_native*.so

# Build the extension
print_status "Building extension..."
if python3 setup.py build_ext --inplace; then
    print_success "Extension built successfully!"
else
    print_error "Build failed!"
    exit 1
fi

# Verify the extension was created
if [ -f nfc_native*.so ]; then
    print_success "Extension module created: $(ls nfc_native*.so)"
else
    print_error "Extension module not found after build"
    exit 1
fi

# Test import
print_status "Testing import..."
if python3 -c 'import nfc_native; print("nfc_native imported successfully")' 2>/dev/null; then
    print_success "Extension module imports correctly"
else
    print_error "Extension module failed to import"
    print_error "Check library dependencies with: ldd nfc_native*.so"
    exit 1
fi

# Test high-level module
print_status "Testing high-level module..."
if python3 -c 'import nfc_reader; print("nfc_reader imported successfully")' 2>/dev/null; then
    print_success "High-level module imports correctly"
else
    print_error "High-level module failed to import"
    exit 1
fi

# Check permissions
if [ "$(id -u)" -ne 0 ]; then
    print_warning "Not running as root - NFC operations may require sudo"
fi

print_success "Build completed successfully!"
print_status ""
print_status "Next steps:"
print_status "1. Test with: sudo python3 example_text_reader.py --simple"
print_status "2. Or use in your code: import nfc_reader"
print_status ""
print_status "For continuous monitoring: sudo python3 example_text_reader.py --monitor"
print_status "For advanced features: sudo python3 example_text_reader.py --advanced"