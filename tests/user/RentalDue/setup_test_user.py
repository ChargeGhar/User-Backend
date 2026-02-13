"""
Setup user for rental testing
"""
import subprocess

def run_django_command(code):
    """Execute Django shell command"""
    cmd = f'docker exec cg-api-local python manage.py shell -c "{code}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def setup_user():
    """Setup user with all prerequisites"""
    code = """
from api.user.auth.models import User, UserProfile, UserKYC
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from decimal import Decimal

user = User.objects.get(id=1)

# 1. Set user status to ACTIVE
user.status = 'ACTIVE'
user.save()
print('✓ User status: ACTIVE')

# 2. Create/update profile
profile, _ = UserProfile.objects.get_or_create(user=user)
profile.full_name = 'Test User'
profile.phone_number = '+9779800000000'
profile.date_of_birth = '1990-01-01'
profile.address = 'Test Address'
profile.city = 'Kathmandu'
profile.is_profile_complete = True
profile.save()
print('✓ Profile: Complete')

# 3. Create/update KYC
kyc, _ = UserKYC.objects.get_or_create(user=user)
kyc.status = 'APPROVED'
kyc.document_type = 'CITIZENSHIP'
kyc.document_number = 'TEST123'
kyc.save()
print('✓ KYC: APPROVED')

# 4. Create/update wallet
wallet, _ = Wallet.objects.get_or_create(user=user)
wallet.balance = Decimal('100.00')
wallet.is_active = True
wallet.save()
print(f'✓ Wallet: NPR {wallet.balance}')

# 5. Create/update points
points, _ = UserPoints.objects.get_or_create(user=user)
points.current_points = 1000
points.total_points = 1000
points.save()
print(f'✓ Points: {points.current_points}')

# 6. Check for active rentals
from api.user.rentals.models import Rental
active = Rental.objects.filter(
    user=user,
    status__in=['PENDING', 'PENDING_POPUP', 'ACTIVE', 'OVERDUE']
).count()
print(f'✓ Active rentals: {active}')

# 7. Check for pending dues
pending_dues = Rental.objects.filter(
    user=user,
    payment_status='PENDING',
    status__in=['OVERDUE', 'COMPLETED']
).count()
print(f'✓ Pending dues: {pending_dues}')

print('\\n✅ User setup complete!')
"""
    output = run_django_command(code)
    print(output)

if __name__ == "__main__":
    print("="*70)
    print("SETTING UP USER FOR RENTAL TESTING")
    print("="*70)
    print()
    setup_user()
