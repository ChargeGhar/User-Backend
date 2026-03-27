#!/bin/bash

# ChargeGhar Production Deployment Script (Manual Fallback)
# ---------------------------------------------------------
# Use this when you need to deploy manually outside of CI/CD.
# For automated deploys, pushes to 'main' branch trigger GitHub Actions.
#
# Prerequisites:
#   - Docker authenticated with GHCR: docker login ghcr.io
#   - .env file present at /opt/powerbank/.env with production values
#
# Usage:
#   sudo ./deploy-production.sh
#   sudo ./deploy-production.sh --first-time   # For initial server setup

set -e

# Configuration
PROJECT_DIR="/opt/powerbank"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
REPO_URL="https://github.com/ChargeGhar/User-Backend.git"
BRANCH="main"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error()  { echo -e "${RED}[✗]${NC} $1"; }
print_step()   { echo -e "${BLUE}[STEP]${NC} $1"; }
print_warning(){ echo -e "${YELLOW}[!]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   exit 1
fi

# ──────────────────────────────────────────────
# First-time setup mode
# ──────────────────────────────────────────────
if [[ "$1" == "--first-time" ]]; then
    echo ""
    echo -e "${BLUE}🔧 First-Time Production Setup${NC}"
    echo "==============================="
    echo ""

    # Create project directory
    if [[ ! -d "$PROJECT_DIR" ]]; then
        mkdir -p "$PROJECT_DIR"
        print_status "Created $PROJECT_DIR"
    fi
    cd "$PROJECT_DIR"

    # Clone repository
    if [[ ! -d ".git" ]]; then
        print_step "Cloning repository..."
        git clone "$REPO_URL" .
        git checkout "$BRANCH"
        print_status "Repository cloned"
    else
        print_status "Repository already exists"
    fi

    # Check .env exists
    if [[ ! -f ".env" ]]; then
        print_error ".env file not found!"
        print_error "Copy your production .env file to $PROJECT_DIR/.env before continuing."
        exit 1
    fi

    # Configure .env for production
    print_step "Configuring .env for production..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

    sed -i 's|ENVIRONMENT=local|ENVIRONMENT=production|' .env
    sed -i 's|DJANGO_DEBUG=true|DJANGO_DEBUG=false|' .env
    sed -i 's|CELERY_TASK_ALWAYS_EAGER=true|CELERY_TASK_ALWAYS_EAGER=false|' .env
    sed -i 's|CELERY_TASK_EAGER_PROPAGATES=true|CELERY_TASK_EAGER_PROPAGATES=false|' .env
    sed -i 's|CELERY_TASK_IGNORE_RESULT=true|CELERY_TASK_IGNORE_RESULT=false|' .env
    sed -i 's|POSTGRES_HOST=pgbouncer|POSTGRES_HOST=db|' .env
    sed -i 's|BASE_URL=http://localhost:8010|BASE_URL=https://main.chargeghar.com|' .env
    print_status ".env configured for production"

    # Create required directories
    mkdir -p logs staticfiles backups
    print_status "Directories created"

    # Authenticate with GHCR
    print_step "Docker login to GHCR..."
    echo ""
    echo "You need a GitHub Personal Access Token (PAT) with 'read:packages' scope."
    echo "Create one at: https://github.com/settings/tokens"
    echo ""
    read -p "Enter your GitHub username: " gh_user
    read -sp "Enter your GitHub PAT: " gh_pat
    echo ""
    echo "$gh_pat" | docker login ghcr.io -u "$gh_user" --password-stdin
    print_status "Authenticated with GHCR"

    echo ""
    print_status "First-time setup complete! Now running deployment..."
    echo ""
fi

# ──────────────────────────────────────────────
# Standard Deployment (pull + recreate)
# ──────────────────────────────────────────────
echo ""
echo -e "${BLUE}🚀 ChargeGhar Production Deployment${NC}"
echo "====================================="

cd "$PROJECT_DIR"

# Verify .env exists
if [[ ! -f ".env" ]]; then
    print_error ".env file not found at $PROJECT_DIR/.env"
    print_error "Run with --first-time flag for initial setup."
    exit 1
fi

# Pull latest code (for compose file, scripts, etc.)
if [[ -d ".git" ]]; then
    print_step "Pulling latest code..."
    git pull origin "$BRANCH" || print_warning "Git pull failed, using existing code"
fi

# Pull the pre-built Docker image from GHCR
print_step "Pulling latest Docker image from GHCR..."
docker-compose -f "$DOCKER_COMPOSE_FILE" pull
print_status "Image pulled"

# Recreate containers with new image (only changed containers restart)
print_step "Recreating containers..."
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d --remove-orphans
print_status "Containers started"

# Clean up old images
docker image prune -f > /dev/null 2>&1
print_status "Old images cleaned"

# Wait for API health
print_step "Waiting for API to be healthy..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8010/api/app/health > /dev/null 2>&1; then
        print_status "API is healthy!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        print_error "Health check timed out after 150 seconds"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs api --tail=30
        exit 1
    fi
    sleep 5
done

# Show status
echo ""
print_step "Container Status:"
docker-compose -f "$DOCKER_COMPOSE_FILE" ps
echo ""

# Check for failed services
FAILED=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps --format "table {{.Service}}\t{{.Status}}" 2>/dev/null | grep -v "Exit 0" | grep -v "SERVICE" | grep -v "running" | grep -v "healthy" | grep -v "migrations" | grep -v "collectstatic" || true)
if [[ -n "$FAILED" ]]; then
    print_warning "Some services may need attention:"
    echo "$FAILED"
fi

# Final output
API_PORT=$(grep "API_PORT" .env | cut -d '=' -f2 | tr -d ' ')
echo ""
print_status "🎉 Deployment Complete!"
print_status "========================"
print_status "API URL: https://main.chargeghar.com"
print_status "API Docs: https://main.chargeghar.com/docs/"
print_status "Admin: https://main.chargeghar.com/admin/"
print_status ""
print_status "Use 'python3 mgr.py' for management tasks"
echo ""