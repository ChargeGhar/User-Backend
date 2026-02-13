#!/bin/bash
# Helper script to set wallet and points balance for testing

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <wallet_balance> <points>"
    echo "Example: $0 200.00 10000"
    exit 1
fi

WALLET=$1
POINTS=$2

echo "Setting balance..."
echo "  Wallet: NPR $WALLET"
echo "  Points: $POINTS"

docker exec cg-api-local python manage.py shell -c "
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from decimal import Decimal

user = User.objects.get(id=1)

# Set wallet
wallet, _ = Wallet.objects.get_or_create(user=user)
wallet.balance = Decimal('$WALLET')
wallet.save()

# Set points
points, _ = UserPoints.objects.get_or_create(user=user)
points.current_points = $POINTS
points.save()

print(f'✅ Wallet: {wallet.balance}')
print(f'✅ Points: {points.current_points}')
" 2>/dev/null | grep "✅"

echo "✅ Balance updated"
