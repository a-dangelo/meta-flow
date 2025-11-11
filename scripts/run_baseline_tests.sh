#!/bin/bash

# Run baseline tests for meta-agent v2 with all providers
# This script tests all example specifications with each provider

echo "============================================="
echo "META-AGENT V2 BASELINE TESTING"
echo "============================================="
echo "Date: $(date)"
echo ""

# Create results directory
RESULTS_DIR="logs/baseline_tests_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Test specifications
SPECS=(
    "simple_sequential.txt"
    "conditional_branch.txt"
    "nested_workflow.txt"
    "parallel_example.txt"
    "orchestrator_example.txt"
)

# Providers to test (only those with API keys configured)
PROVIDERS=()

# Check which providers are available
if [ ! -z "$AIMLAPI_KEY" ]; then
    PROVIDERS+=("aimlapi")
fi

if [ ! -z "$GEMINI_API_KEY" ]; then
    PROVIDERS+=("gemini")
fi

if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    PROVIDERS+=("claude")
fi

if [ ${#PROVIDERS[@]} -eq 0 ]; then
    echo "ERROR: No API keys configured. Please set at least one of:"
    echo "  - AIMLAPI_KEY"
    echo "  - GEMINI_API_KEY"
    echo "  - ANTHROPIC_API_KEY"
    exit 1
fi

echo "Available providers: ${PROVIDERS[@]}"
echo "Test specifications: ${SPECS[@]}"
echo "Results directory: $RESULTS_DIR"
echo ""

# Summary results
declare -A RESULTS

# Run tests
for provider in "${PROVIDERS[@]}"; do
    echo "============================================="
    echo "Testing with provider: $provider"
    echo "============================================="

    for spec in "${SPECS[@]}"; do
        echo ""
        echo "Testing: $spec"
        echo "---------------------------------------------"

        # Create log file name
        log_file="$RESULTS_DIR/${provider}_${spec%.txt}.log"

        # Run test and capture output
        python tests/test_v2_with_example.py \
            --spec "specs/examples/$spec" \
            --provider "$provider" \
            --log-dir "$RESULTS_DIR" \
            > "$log_file" 2>&1

        # Check exit code
        if [ $? -eq 0 ]; then
            echo "✅ SUCCESS: $provider - $spec"
            RESULTS["$provider-$spec"]="SUCCESS"
        else
            echo "❌ FAILED: $provider - $spec"
            RESULTS["$provider-$spec"]="FAILED"

            # Show last error from log
            echo "Error details:"
            tail -n 20 "$log_file" | grep -E "(ERROR|Error|error|Exception)" | head -n 3
        fi
    done
    echo ""
done

# Print summary
echo ""
echo "============================================="
echo "SUMMARY OF RESULTS"
echo "============================================="
echo ""

# Calculate success rates per provider
for provider in "${PROVIDERS[@]}"; do
    success_count=0
    total_count=0

    echo "Provider: $provider"
    echo "---------------------------------------------"

    for spec in "${SPECS[@]}"; do
        key="$provider-$spec"
        result="${RESULTS[$key]}"

        if [ ! -z "$result" ]; then
            total_count=$((total_count + 1))
            if [ "$result" == "SUCCESS" ]; then
                success_count=$((success_count + 1))
                echo "  ✅ $spec"
            else
                echo "  ❌ $spec"
            fi
        fi
    done

    if [ $total_count -gt 0 ]; then
        success_rate=$((success_count * 100 / total_count))
        echo ""
        echo "  Success rate: $success_count/$total_count ($success_rate%)"
    fi
    echo ""
done

echo "Full logs available in: $RESULTS_DIR"
echo ""
echo "To view a specific log:"
echo "  cat $RESULTS_DIR/<provider>_<spec>.log"
echo ""
echo "============================================="
echo "BASELINE TESTING COMPLETE"
echo "============================================="