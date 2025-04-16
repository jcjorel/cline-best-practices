#!/bin/bash

# Script to analyze component dependencies and detect potential issues
# This script scans the Python code for component dependencies and checks for potential issues

echo "=== DBP Component Dependency Analyzer ==="
echo "Scanning component files..."

# Define directories to search
SRC_DIR="src/dbp"
COMPONENT_PATTERN="class.*Component"

# Find all component classes
echo -e "\n=== Found Components ==="
grep -r "$COMPONENT_PATTERN" --include="*.py" $SRC_DIR | sort

# Find all component name declarations
echo -e "\n=== Component Names ==="
grep -r "def name" --include="*.py" --after-context=3 $SRC_DIR | grep "return" | sort

# Find all dependency declarations
echo -e "\n=== Component Dependencies ==="
grep -r "def dependencies" --include="*.py" --after-context=5 $SRC_DIR | grep -E "return|dependencies" | sort

# Search for potential circular dependencies
echo -e "\n=== Potential Circular Dependencies ==="
for file in $(find $SRC_DIR -name "*.py" -type f); do
    component=$(grep -l "class.*Component" $file)
    if [ -n "$component" ]; then
        component_name=$(grep -A 3 "def name" $file | grep "return" | sed -E 's/.*return "([^"]+)".*/\1/')
        if [ -n "$component_name" ]; then
            dependencies=$(grep -A 5 "def dependencies" $file | grep -E "return \[" | sed -E 's/.*return \[(.*)\].*/\1/')
            if grep -q "$component_name" <(echo "$dependencies"); then
                echo "WARNING: Possible self-dependency in $file"
                echo "  Component: $component_name"
                echo "  Dependencies: $dependencies"
            fi
        fi
    fi
done

# Look for dependency mismatches
echo -e "\n=== Checking for Component Name Mismatches ==="
# Extract all component names
component_names=$(grep -r "def name" --include="*.py" --after-context=3 $SRC_DIR | grep "return" | sed -E 's/.*return "([^"]+)".*/\1/' | sort)

# Check each dependency
for file in $(find $SRC_DIR -name "*.py" -type f); do
    component=$(grep -l "class.*Component" $file)
    if [ -n "$component" ]; then
        dependencies=$(grep -A 5 "def dependencies" $file | grep -E "return \[" | sed -E 's/.*return \[(.*)\].*/\1/' | tr ',' '\n' | sed -E 's/[" ]//g')
        for dep in $dependencies; do
            if ! echo "$component_names" | grep -q "^$dep$"; then
                component_name=$(grep -A 3 "def name" $file | grep "return" | sed -E 's/.*return "([^"]+)".*/\1/')
                echo "WARNING: Component '$component_name' depends on '$dep' which might not exist"
            fi
        done
    fi
done

echo -e "\nAnalysis complete. See above for potential issues."
