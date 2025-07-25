#!/bin/bash

# Learntrac Display Plugin Installation Script

echo "Installing Learntrac Display Plugin..."
echo "======================================"

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "Error: setup.py not found. Please run this script from the plugin directory."
    exit 1
fi

# Build the egg file
echo "Building plugin egg..."
python setup.py bdist_egg

if [ $? -ne 0 ]; then
    echo "Error: Failed to build egg file"
    exit 1
fi

# Find the generated egg file
EGG_FILE=$(ls dist/*.egg 2>/dev/null | head -n 1)

if [ -z "$EGG_FILE" ]; then
    echo "Error: No egg file found in dist/"
    exit 1
fi

echo "Successfully built: $EGG_FILE"

# Check if plugins directory is provided
if [ -n "$1" ]; then
    PLUGINS_DIR="$1"
else
    # Try to find the plugins directory
    if [ -d "../../plugins" ]; then
        PLUGINS_DIR="../../plugins"
    else
        echo ""
        echo "Usage: ./install.sh [plugins_directory]"
        echo ""
        echo "Example: ./install.sh /path/to/trac/plugins/"
        exit 0
    fi
fi

# Copy the egg file
if [ -d "$PLUGINS_DIR" ]; then
    echo "Copying to plugins directory: $PLUGINS_DIR"
    cp "$EGG_FILE" "$PLUGINS_DIR/"
    
    if [ $? -eq 0 ]; then
        echo "✓ Plugin installed successfully!"
        echo ""
        echo "Next steps:"
        echo "1. Add to your trac.ini:"
        echo "   [components]"
        echo "   learntrac_display.* = enabled"
        echo ""
        echo "2. Restart Trac"
    else
        echo "Error: Failed to copy egg file"
        exit 1
    fi
else
    echo "Plugins directory not found: $PLUGINS_DIR"
    echo "Please specify the correct path to your Trac plugins directory"
    exit 1
fi