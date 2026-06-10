#!/bin/bash
# Check if python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 could not be found. Please install it to continue."
    exit
fi

# Run the installer/launcher
python3 install.py
