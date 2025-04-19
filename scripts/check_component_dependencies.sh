#!/bin/bash

# This script verifies that all components in the system properly follow
# the new component dependency declaration pattern.

echo "Checking components for proper dependency implementation..."
echo "========================================================"

# Search for initialize method implementations that still use context.get_component
echo "1. Checking for components still using context.get_component()..."
grep -r "context\.get_component" --include="*.py" src/dbp/*/component*.py

if [ $? -eq 0 ]; then
  echo "❌ Found components still using context.get_component() - these need to be updated!"
else
  echo "✅ No components using context.get_component() - good!"
fi

# Search for any remaining dependencies properties
echo ""
echo "2. Checking for components still implementing dependencies property..."
grep -r "@property" -A 2 -B 2 --include="*.py" src/dbp/*/component*.py | grep "dependencies"

if [ $? -eq 0 ]; then
  echo "❌ Found components still implementing dependencies property - these need to be updated!"
else
  echo "✅ No components with dependencies property - good!"
fi

# Check for initialize methods without dependencies parameter
echo ""
echo "3. Checking for initialize methods without dependencies parameter..."
grep -r "def initialize" -A 2 --include="*.py" src/dbp/*/component*.py | grep -v "dependencies"

if [ $? -eq 0 ]; then
  echo "❌ Found initialize methods that might not accept dependencies parameter - verify these!"
else
  echo "✅ All initialize methods appear to accept dependencies parameter - good!"
fi

# Check that components follow the dependency injection pattern
echo ""
echo "4. Checking for proper dependency injection pattern usage..."
echo "Sample of initialize methods that use get_dependency correctly:"
grep -r "self.get_dependency" --include="*.py" src/dbp/*/component*.py | head -n 5

echo ""
echo "Verification complete. Please review any findings above."
echo "Components should follow the pattern:"
echo "def initialize(self, context: InitializationContext, dependencies: Dict[str, Component]) -> None:"
echo "    component = self.get_dependency(dependencies, \"component_name\")"
