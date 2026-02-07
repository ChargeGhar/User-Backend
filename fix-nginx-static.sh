#!/bin/bash

echo "🔧 Fixing Nginx Static Files Configuration"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

# Check current Nginx configuration
print_step "Checking current Nginx configuration..."
echo "Current Nginx sites:"
ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "No sites-enabled directory found"

# Find Nginx config for main.chargeghar.com
print_step "Looking for main.chargeghar.com configuration..."
NGINX_CONFIG=$(find /etc/nginx -name "*.conf" -exec grep -l "main.chargeghar.com" {} \; 2>/dev/null | head -1)

if [[ -z "$NGINX_CONFIG" ]]; then
    # Check sites-available and sites-enabled
    NGINX_CONFIG=$(find /etc/nginx/sites-* -type f -exec grep -l "main.chargeghar.com" {} \; 2>/dev/null | head -1)
fi

if [[ -n "$NGINX_CONFIG" ]]; then
    print_status "Found Nginx config: $NGINX_CONFIG"
    
    print_step "Current configuration:"
    cat "$NGINX_CONFIG"
    
    print_step "Adding static files configuration..."
    
    # Backup original config
    cp "$NGINX_CONFIG" "$NGINX_CONFIG.backup"
    
    # Check if static location already exists
    if grep -q "location /static/" "$NGINX_CONFIG"; then
        print_warning "Static location already exists in config"
    else
        # Add static files location before the main location block
        sed -i '/location \/ {/i\
    # Serve static files\
    location /static/ {\
        alias /opt/powerbank/staticfiles/;\
        expires 1y;\
        add_header Cache-Control "public, immutable";\
    }\
' "$NGINX_CONFIG"
        
        print_status "Added static files configuration"
    fi
    
    # Create symbolic link from container static files to host
    print_step "Creating static files link..."
    
    # Get static files from container
    API_CONTAINER=$(docker ps --format "{{.Names}}" | grep "cg-api" | head -1)
    
    if [[ -n "$API_CONTAINER" ]]; then
        # Copy static files from container to host
        mkdir -p /opt/powerbank/staticfiles
        docker cp "$API_CONTAINER:/application/staticfiles/." /opt/powerbank/staticfiles/
        
        print_status "Copied static files from container to host"
        
        # Set proper permissions
        chown -R www-data:www-data /opt/powerbank/staticfiles/ 2>/dev/null || true
        chmod -R 755 /opt/powerbank/staticfiles/
        
        print_status "Set proper permissions"
    else
        print_warning "No API container found"
    fi
    
    # Test Nginx configuration
    print_step "Testing Nginx configuration..."
    if nginx -t; then
        print_status "Nginx configuration is valid"
        
        # Reload Nginx
        print_step "Reloading Nginx..."
        systemctl reload nginx
        print_status "Nginx reloaded"
        
        # Test static file access
        print_step "Testing static file access..."
        sleep 2
        
        if curl -I https://main.chargeghar.com/static/admin/css/base.css 2>/dev/null | grep -q "200 OK"; then
            print_status "✅ Static files are now working!"
        else
            print_warning "Static files still not accessible, checking..."
            curl -I https://main.chargeghar.com/static/admin/css/base.css
        fi
        
    else
        print_warning "Nginx configuration has errors, restoring backup"
        cp "$NGINX_CONFIG.backup" "$NGINX_CONFIG"
    fi
    
else
    print_warning "Could not find Nginx configuration for main.chargeghar.com"
    print_step "Available Nginx configurations:"
    find /etc/nginx -name "*.conf" -type f 2>/dev/null | head -5
fi

print_status "Nginx static files fix completed!"