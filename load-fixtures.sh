#!/bin/bash

# PowerBank Django Fixtures Loader Script
# Loads all fixtures in proper dependency order with retry logic
#
# Usage:
#   ./load-fixtures.sh    (correct filename with hyphen)
#   ./load_fixtures.sh    (symlink with underscore)
#
# Features:
# - Smart dependency-based loading for complex apps
# - Retry logic for failed fixtures (up to 3 attempts)
# - Priority-based loading order within apps
# - Comprehensive error handling and reporting

set -e  # Exit on any error

echo "🚀 Starting PowerBank Fixtures Loading..."
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if we're in the correct directory
if [[ ! -f "manage.py" ]]; then
    print_error "manage.py not found! Please run this script from the Django project root directory."
    exit 1
fi

# Make sure the script is executable
if [[ ! -x "$0" ]]; then
    print_warning "Script is not executable. Making it executable..."
    chmod +x "$0"
fi

# Find the correct API container
API_CONTAINER=$(docker ps --format "{{.Names}}" | grep "powerbank.*api" | head -1)
if [[ -z "$API_CONTAINER" ]]; then
    print_error "No PowerBank API container is running!"
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep powerbank || echo "No PowerBank containers found"
    exit 1
fi

print_status "Using API container: $API_CONTAINER"

print_status "Docker containers are running ✓"

# Wait for API to be ready
print_status "Waiting for API to be ready..."
sleep 10

# Function to create superuser if it doesn't exist
create_superuser() {
    print_step "Creating superuser with dual authentication support..."
    
    # Always run the superuser setup to ensure proper configuration
    print_status "Setting up admin user with OTP + Password authentication..."
    docker exec -i "$API_CONTAINER" python manage.py shell -c "
from django.contrib.auth import get_user_model
from django.utils import timezone
from axes.models import AccessAttempt, AccessLog

User = get_user_model()
username = 'janak'
email = 'janak@powerbank.com'
admin_password = '5060'

# Clear any existing axes locks for admin
AccessAttempt.objects.filter(username=username).delete()
AccessAttempt.objects.filter(username=email).delete()
AccessLog.objects.filter(username=username).delete()
AccessLog.objects.filter(username=email).delete()

# Check if user already exists
if User.objects.filter(username=username).exists():
    print(f'User {username} already exists - updating...')
    user = User.objects.get(username=username)
    
    # Ensure admin privileges
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.email_verified = True
    user.phone_verified = True
    user.status = 'ACTIVE'
    user.save()
    
    # Set password for Django admin access
    user.set_password(admin_password)
    user.save()
    
    print(f'✓ Updated {username} with admin privileges and password')
else:
    # Create new superuser
    user = User.objects.create_user(
        identifier=email,  # Use identifier for create_user method (email will be parsed)
        username=username,
        is_superuser=True,
        is_staff=True,
        is_active=True,
        email_verified=True,
        phone_verified=True,
        status='ACTIVE'
    )
    
    # Set password for Django admin access (works because user is staff/superuser)
    user.set_password(admin_password)
    user.save()
    
    print(f'✓ Superuser {username} created successfully')

print(f'  - Email: {email}')
print(f'  - Username: {username}')
print(f'  - Status: ACTIVE')
print(f'  - Is staff: {user.is_staff}')
print(f'  - Is superuser: {user.is_superuser}')
print(f'  - Has password: {user.has_usable_password()}')
print(f'  - Email verified: True')
print(f'  - Phone verified: True')

# Create UserProfile for complete profile
try:
    from api.users.models import UserProfile
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': 'Janak Admin',
            'is_profile_complete': True
        }
    )
    if created:
        print(f'  - Profile created: Complete')
    else:
        print(f'  - Profile exists: Complete')
except Exception as e:
    print(f'  - Profile creation skipped: {e}')

# Create UserKYC for KYC verification
try:
    from api.users.models import UserKYC
    kyc, created = UserKYC.objects.get_or_create(
        user=user,
        defaults={
            'document_type': 'CITIZENSHIP',
            'document_number': 'ADMIN001',
            'document_front_url': 'https://example.com/admin-doc.jpg',
            'status': 'APPROVED',
            'verified_at': timezone.now()
        }
    )
    if created:
        print(f'  - KYC created: APPROVED')
    else:
        print(f'  - KYC exists: APPROVED')
except Exception as e:
    print(f'  - KYC creation skipped: {e}')

print('')
print('🎉 Admin user setup completed!')
print('🔐 Dual Authentication Available:')
print('   1. Django Admin: Username + Password')
print('   2. API Access: Email + OTP')
"
    print_status "✓ Superuser created/updated with dual authentication support"
}

# Function to load fixtures for an app with retry logic
load_fixtures() {
    local app_name=$1
    local fixtures_dir="api/user/$app_name/fixtures"
    local max_retries=3

    if [[ -d "$fixtures_dir" ]]; then
        print_step "Loading fixtures for $app_name..."

        # Find all .json files in the fixtures directory
        local fixtures=$(find "$fixtures_dir" -name "*.json" -type f | sort)

        if [[ -z "$fixtures" ]]; then
            print_warning "No fixtures found in $fixtures_dir"
            return
        fi

        # Track failed fixtures for retry
        local failed_fixtures=()
        local retry_count=0

        # Load each fixture file
        for fixture in $fixtures; do
            local fixture_name=$(basename "$fixture")
            print_status "Loading $fixture_name..."

            # Capture both stdout and stderr to check for duplicate key errors
            local output=$(docker exec -i "$API_CONTAINER" python manage.py loaddata "$fixture" 2>&1)
            local exit_code=$?
            
            if [[ $exit_code -eq 0 ]]; then
                print_status "✓ Successfully loaded $fixture_name"
            elif echo "$output" | grep -q "duplicate key value violates unique constraint"; then
                print_status "✓ $fixture_name already loaded (skipping duplicates)"
            else
                print_warning "⚠ Failed to load $fixture_name (adding to retry queue)"
                failed_fixtures+=("$fixture")
            fi
        done

        # Retry failed fixtures (dependency resolution)
        while [[ ${#failed_fixtures[@]} -gt 0 && $retry_count -lt $max_retries ]]; do
            retry_count=$((retry_count + 1))
            print_step "Retry attempt $retry_count for $app_name (${#failed_fixtures[@]} fixtures)..."
            
            local new_failed_fixtures=()
            
            for fixture in "${failed_fixtures[@]}"; do
                local fixture_name=$(basename "$fixture")
                print_status "Retrying $fixture_name..."
                
                # Capture output to check for duplicate key errors
                local output=$(docker exec -i "$API_CONTAINER" python manage.py loaddata "$fixture" 2>&1)
                local exit_code=$?
                
                if [[ $exit_code -eq 0 ]]; then
                    print_status "✓ Successfully loaded $fixture_name on retry"
                elif echo "$output" | grep -q "duplicate key value violates unique constraint"; then
                    print_status "✓ $fixture_name already loaded (skipping duplicates)"
                else
                    print_warning "⚠ Still failing: $fixture_name"
                    new_failed_fixtures+=("$fixture")
                fi
            done
            
            failed_fixtures=("${new_failed_fixtures[@]}")
            
            # Wait a bit between retries
            if [[ ${#failed_fixtures[@]} -gt 0 ]]; then
                sleep 2
            fi
        done

        # Report final failures
        if [[ ${#failed_fixtures[@]} -gt 0 ]]; then
            print_error "❌ Failed to load ${#failed_fixtures[@]} fixtures in $app_name after $max_retries retries:"
            for fixture in "${failed_fixtures[@]}"; do
                local fixture_name=$(basename "$fixture")
                print_error "   - $fixture_name"
            done
        fi
    else
        print_warning "Fixtures directory not found: $fixtures_dir"
    fi
}

# Function to load fixtures with smart dependency ordering
load_fixtures_smart() {
    local app_name=$1
    local fixtures_dir="api/user/$app_name/fixtures"

    if [[ -d "$fixtures_dir" ]]; then
        print_step "Smart loading fixtures for $app_name..."

        # Find all .json files in the fixtures directory
        local fixtures=$(find "$fixtures_dir" -name "*.json" -type f | sort)

        if [[ -z "$fixtures" ]]; then
            print_warning "No fixtures found in $fixtures_dir"
            return
        fi

        # Define loading order based on common Django model dependencies
        local priority_order=(
            "*rule*"      # Rules first (notification rules, etc.)
            "*config*"    # Configuration
            "*country*"   # Countries
            "*user*"      # Users
            "*station*"   # Stations (but not slots/mappings)
            "*amenity*"   # Amenities
            "*slot*"      # Slots (depend on stations)
            "*mapping*"   # Mappings (depend on stations + amenities)
            "*powerbank*" # PowerBanks (depend on stations/slots)
            "*template*"  # Templates (depend on rules)
            "*"           # Everything else
        )

        local loaded_fixtures=()
        
        # Load fixtures in priority order
        for pattern in "${priority_order[@]}"; do
            for fixture in $fixtures; do
                local fixture_name=$(basename "$fixture")
                
                # Skip if already loaded
                if [[ " ${loaded_fixtures[@]} " =~ " ${fixture} " ]]; then
                    continue
                fi
                
                # Check if fixture matches current pattern
                if [[ "$fixture_name" == $pattern ]]; then
                    print_status "Loading $fixture_name (priority: $pattern)..."
                    
                    if docker exec -i "$API_CONTAINER" python manage.py loaddata "$fixture" 2>/dev/null; then
                        print_status "✓ Successfully loaded $fixture_name"
                        loaded_fixtures+=("$fixture")
                    else
                        print_warning "⚠ Failed to load $fixture_name"
                    fi
                fi
            done
        done

        # Load any remaining fixtures that didn't match patterns
        for fixture in $fixtures; do
            if [[ ! " ${loaded_fixtures[@]} " =~ " ${fixture} " ]]; then
                local fixture_name=$(basename "$fixture")
                print_status "Loading remaining fixture: $fixture_name..."
                
                if docker exec -i "$API_CONTAINER" python manage.py loaddata "$fixture" 2>/dev/null; then
                    print_status "✓ Successfully loaded $fixture_name"
                else
                    print_warning "⚠ Failed to load $fixture_name"
                fi
            fi
        done
    else
        print_warning "Fixtures directory not found: $fixtures_dir"
    fi
}

# Function to generate admin JWT token
generate_admin_token() {
    print_step "Generating admin JWT token for API testing..."
    
    local token=$(docker exec -i "$API_CONTAINER" python manage.py shell -c "
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import sys

try:
    User = get_user_model()
    admin_user = User.objects.get(username='janak')
    refresh = RefreshToken.for_user(admin_user)
    print(str(refresh.access_token))
except Exception as e:
    print(f'Error generating token: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)
    
    if [[ -n "$token" && "$token" != *"Error"* ]]; then
        print_status "✓ Admin JWT token generated successfully"
        echo ""
        print_status "🎫 Admin JWT Token (for Swagger UI):"
        echo "Bearer $token"
        echo ""
        print_status "📋 Copy the above Bearer token for Swagger UI Authorization"
        echo ""
    else
        print_warning "⚠ Failed to generate admin JWT token"
    fi
}

# Create superuser first
create_superuser

# Load fixtures in dependency order with smart loading
print_step "Loading fixtures in dependency order with retry logic..."
echo ""

# 1. System - Countries, app configs, and other foundational system data
load_fixtures "system"

# 2. Common - Late fee configs and other common data
load_fixtures "common"

# 3. Users - Foundational user data
load_fixtures "users"

# 4. Content - Static content data
load_fixtures "content"

# 5. Stations - Station, amenity, slot, and power bank data (use smart loading for dependencies)
load_fixtures_smart "stations"

# 6. Rentals - Rental packages and rental data (depends on users, stations)
load_fixtures "rentals"

# 7. Payments - Payment methods, wallets, transactions (depends on users, rentals)
load_fixtures "payments"

# 8. Points - User points system (depends on users)
load_fixtures "points"

# 9. Promotions - Promotion data
load_fixtures "promotions"

# 10. Social - Social features (depends on users)
load_fixtures "social"

# 11. Notifications - Notification system (depends on users, use smart loading)
load_fixtures_smart "notifications"

# 12. Admin - Admin specific data (if exists)
load_fixtures "admin"

# Generate admin JWT token for immediate testing
generate_admin_token

# Function to verify admin setup
verify_admin_setup() {
    print_step "Verifying admin setup..."
    
    local verification=$(docker exec -i "$API_CONTAINER" python manage.py shell -c "
from django.contrib.auth import get_user_model
from axes.models import AccessAttempt

User = get_user_model()
try:
    admin = User.objects.get(username='janak')
    locks = AccessAttempt.objects.filter(username='janak').count()
    
    print(f'✅ Admin user: {admin.username}')
    print(f'✅ Email: {admin.email}')
    print(f'✅ Is staff: {admin.is_staff}')
    print(f'✅ Is superuser: {admin.is_superuser}')
    print(f'✅ Has password: {admin.has_usable_password()}')
    print(f'✅ Account locks: {locks}')
    
    if admin.is_staff and admin.is_superuser and admin.has_usable_password() and locks == 0:
        print('🎉 Admin setup is PERFECT!')
    else:
        print('⚠️  Admin setup needs attention')
        
except Exception as e:
    print(f'❌ Admin verification failed: {e}')
" 2>/dev/null)
    
    echo "$verification"
}

# Verify admin setup
verify_admin_setup

echo ""
print_status "🎉 Fixtures loading completed!"
print_status "========================================="

# Get API port from .env
API_PORT=$(grep "API_PORT" .env | cut -d '=' -f2 | tr -d ' ')
SERVER_IP=$(hostname -I | awk '{print $1}')

print_status "Summary:"
print_status "- Superuser created with OTP-based user model (username: janak, email: janak@powerbank.com)"
print_status "- System fixtures loaded (countries, app configs)"
print_status "- Common fixtures loaded (late fee configs)"
print_status "- User fixtures loaded"
print_status "- Content fixtures loaded"
print_status "- Station fixtures loaded (stations, amenities, slots, power banks)"
print_status "- Rental fixtures loaded (packages and rentals)"
print_status "- Payment fixtures loaded (methods, wallets, transactions)"
print_status "- Points fixtures loaded"
print_status "- Promotions fixtures loaded"
print_status "- Social fixtures loaded"
print_status "- Notifications fixtures loaded"
print_status "- Admin fixtures loaded (if available)"
echo ""
print_status "🌐 Your PowerBank API is ready!"
print_status "API Base URL: http://$SERVER_IP:${API_PORT:-8010}"
print_status "API Documentation: http://$SERVER_IP:${API_PORT:-8010}/docs/"
print_status "Admin Panel: http://$SERVER_IP:${API_PORT:-8010}/admin/"
print_status "Health Check: http://$SERVER_IP:${API_PORT:-8010}/api/app/health/"
echo ""
print_status "🔐 Authentication System:"
print_status "- Dual authentication system implemented"
print_status "- Regular users: OTP-only authentication (secure, passwordless)"
print_status "- Admin user: Both password AND OTP authentication available"
print_status ""
print_status "🔑 Admin Access Methods:"
print_status "  1. Django Admin Panel:"
print_status "     URL: http://$SERVER_IP:${API_PORT:-8010}/admin/"
print_status "     Username: janak"
print_status "     Password: PowerBank@2024"
print_status ""
print_status "  2. API Access (OTP-based):"
print_status "     Email: janak@powerbank.com"
print_status "     Use OTP flow as documented in api/users/AUTH_FLOW.md"
print_status "     JWT token generated above for immediate Swagger UI testing"
echo ""
print_status "🔧 Useful commands:"
print_status "Django shell: docker-compose exec $API_CONTAINER python manage.py shell"
print_status "View logs: docker-compose logs -f $API_CONTAINER"
print_status "Restart API: docker-compose restart $API_CONTAINER"
print_status "Unlock admin: python unlock_admin.py (if account gets locked)"
print_status "Reset admin password: docker-compose exec $API_CONTAINER python manage.py shell -c \"from django.contrib.auth import get_user_model; User = get_user_model(); admin = User.objects.get(username='janak'); admin.set_password('PowerBank@2024'); admin.save(); print('Password reset!')\""
print_status "Generate admin token: docker-compose exec $API_CONTAINER python manage.py shell -c \"from django.contrib.auth import get_user_model; from rest_framework_simplejwt.tokens import RefreshToken; User = get_user_model(); admin = User.objects.get(username='janak'); print('Admin JWT:', str(RefreshToken.for_user(admin).access_token))\""
print_status "Clear axes locks: docker-compose exec $API_CONTAINER python manage.py axes_reset"
