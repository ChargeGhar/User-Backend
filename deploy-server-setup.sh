#!/bin/bash

# PowerBank Django Server Setup Script
# This is a lightweight setup since Docker should already be installed for your Java/IoT app

set -e  # Exit on any error

echo "🔧 PowerBank Django Server Setup..."
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   exit 1
fi

print_status "Checking Docker installation..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Installing Docker..."

    # Install Docker
    apt update
    apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up the stable repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    print_status "Docker installed successfully ✓"
else
    print_status "Docker is already installed ✓"
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available. Installing..."

    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

    print_status "Docker Compose installed successfully ✓"
else
    print_status "Docker Compose is available ✓"
fi

# Verify installations
print_status "Verifying installations..."
docker --version
docker-compose --version || docker compose version

# Create powerbank user if it doesn't exist
if ! id -u powerbank &> /dev/null; then
    print_status "Creating powerbank user..."
    useradd -m -s /bin/bash powerbank
    usermod -aG docker powerbank
    print_status "User 'powerbank' created and added to docker group ✓"
else
    print_status "User 'powerbank' already exists ✓"
fi

# Create project directory
PROJECT_DIR="/opt/User-Backend"
if [[ ! -d "$PROJECT_DIR" ]]; then
    print_status "Creating project directory: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
    chown powerbank:powerbank "$PROJECT_DIR"
else
    print_status "Project directory already exists: $PROJECT_DIR"
fi

print_status ""
print_status "🎉 Server setup completed successfully!"
print_status "========================================"
print_status "Docker and Docker Compose are ready for PowerBank deployment"
print_status "Project directory: $PROJECT_DIR"
print_status ""
print_status "Next step: Run the deployment script"
print_status "curl -O https://raw.githubusercontent.com/ChargeGhar/User-Backend/main/deploy-production.sh"
print_status "chmod +x deploy-production.sh"
print_status "./deploy-production.sh"