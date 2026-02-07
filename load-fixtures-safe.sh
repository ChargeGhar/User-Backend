#!/bin/bash

# PowerBank Safe Fixtures Loader Script
# -------------------------------------
# Loads fixtures in an idempotent way using load_fixtures_safe.py
# so it can be run on non-empty databases without failing.
#
# Usage:
#   ./load-fixtures-safe.sh
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Ensure we are in project root
if [[ ! -f "manage.py" ]]; then
    print_error "manage.py not found! Please run this script from the Django project root directory."
    exit 1
fi

# Make sure the script is executable
if [[ ! -x "$0" ]]; then
    print_warning "Script is not executable. Making it executable..."
    chmod +x "$0"
fi

print_step "Starting safe fixtures loading (idempotent)"

# Detect API container (same pattern as load-fixtures.sh)
API_CONTAINER=$(docker ps --format "{{.Names}}" | grep "cg-api" | head -1)
if [[ -z "$API_CONTAINER" ]]; then
    print_error "No ChargeGhar API container is running!"
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep cg- || echo "No ChargeGhar containers found"
    exit 1
fi

print_status "Using API container: $API_CONTAINER"

# Give the API a moment in case it just started
sleep 5

print_step "Running load_fixtures_safe.py inside container..."

if docker exec -i "$API_CONTAINER" python load_fixtures_safe.py; then
    print_status "🎉 Safe fixtures loading completed successfully!"
else
    print_error "Safe fixtures loading encountered errors. Check the output above."
    exit 1
fi
