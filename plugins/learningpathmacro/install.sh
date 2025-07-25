#!/bin/bash
# Installation script for Learning Path Macro plugin

echo "Installing Learning Path Macro for Trac..."

# Get the directory of this script
PLUGIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TRAC_ENV="${TRAC_ENV:-/path/to/trac/env}"

# Check if we're in the right directory
if [ ! -f "$PLUGIN_DIR/setup.py" ]; then
    echo "Error: setup.py not found. Please run this script from the plugin directory."
    exit 1
fi

# Install the plugin in development mode
echo "Installing plugin in development mode..."
cd "$PLUGIN_DIR"
python setup.py develop

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo "Plugin installed successfully!"
else
    echo "Error: Plugin installation failed."
    exit 1
fi

# Provide configuration instructions
echo ""
echo "Next steps:"
echo "1. Add the following to your trac.ini file:"
echo ""
echo "[components]"
echo "learningpathmacro.* = enabled"
echo ""
echo "2. Upgrade your Trac environment to create database tables:"
echo "   trac-admin $TRAC_ENV upgrade"
echo ""
echo "3. Grant permissions as needed:"
echo "   trac-admin $TRAC_ENV permission add authenticated LEARNING_PATH_VIEW"
echo "   trac-admin $TRAC_ENV permission add admin LEARNING_PATH_ADMIN"
echo ""
echo "4. Restart your Trac server"
echo ""
echo "Installation complete!"