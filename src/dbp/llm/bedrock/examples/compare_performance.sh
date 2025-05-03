#!/bin/bash
# Simple script to compare performance between original and optimized model discovery examples

echo "===== Performance Comparison ====="
echo "Running original example (this may take several minutes)..."
time python model_discovery_example.py > original_output.log

echo -e "\nRunning optimized example..."
time python model_discovery_example_optimized.py > optimized_output.log

echo -e "\n===== Results ====="
echo "Original execution times above, optimized execution times below."
echo "Check original_output.log and optimized_output.log for details."
