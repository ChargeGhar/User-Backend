#!/usr/bin/env python3
"""
Test script for payments app functionality

This script tests the payments app endpoints and services
to ensure everything is working correctly.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from django.contrib.auth import get_user_model
from api.user.payments.models import PaymentMethod, Transaction, Wallet
from api.user.payments.services import WalletService, PaymentIntentService
from api.user.payments.serializers import PaymentMethodSerializer, TransactionSerializer

User = get_user_model()

def test_payment_models():
    """Test the payment models functionality"""
    print("🧪 Testing Payment Models...")
    
    try:
        # Create a test payment method
        payment_method = PaymentMethod.objects.create(
            name='Test Khalti',
            gateway='khalti',
            min_amount=10.00,
            max_amount=10000.00,
            supported_currencies=['NPR'],
            configuration={
                'public_key': 'test_key',
                'webhook_url': 'https://example.com/webhook'
            }
        )
        print(f"✅ Created payment method: {payment_method.name}")
        
        # Test payment method serializer
        serializer = PaymentMethodSerializer(payment_method)
        print(f"✅ PaymentMethodSerializer data: {len(serializer.data)} fields")
        
        print("🎉 All payment model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Payment model test failed: {str(e)}")
        return False

def test_wallet_service():
    """Test the wallet service functionality"""
    print("\n🧪 Testing Wallet Service...")
    
    try:
        # Create a test user if it doesn't exist
        user, created = User.objects.get_or_create(
            phone_number='+9779800000001',
            defaults={
                'username': 'testpaymentuser',
                'email': 'testpayment@example.com'
            }
        )
        
        if created:
            print(f"✅ Created test user: {user.phone_number}")
        else:
            print(f"✅ Using existing test user: {user.phone_number}")
        
        # Initialize wallet service
        wallet_service = WalletService()
        
        # Test get or create wallet
        wallet = wallet_service.get_or_create_wallet(user)
        print(f"✅ Created/Retrieved wallet: {wallet.balance} {wallet.currency}")
        
        # Test get wallet balance
        balance = wallet_service.get_wallet_balance(user)
        print(f"✅ Retrieved wallet balance: {balance}")
        
        print("🎉 All wallet service tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Wallet service test failed: {str(e)}")
        return False

def test_payment_intent_service():
    """Test the payment intent service functionality"""
    print("\n🧪 Testing Payment Intent Service...")
    
    try:
        # Get test user and payment method
        user = User.objects.filter(phone_number='+9779800000001').first()
        payment_method = PaymentMethod.objects.first()
        
        if not user or not payment_method:
            print("❌ Test user or payment method not found")
            return False
        
        # Initialize service
        service = PaymentIntentService()
        
        # Test create payment intent
        intent = service.create_topup_intent(
            user=user,
            amount=100.00,
            payment_method_id=payment_method.id
        )
        print(f"✅ Created payment intent: {intent.intent_id}")
        
        # Test get payment status
        status_data = service.get_payment_status(intent.intent_id)
        print(f"✅ Retrieved payment status: {status_data['status']}")
        
        # Test cancel payment intent
        cancel_result = service.cancel_payment_intent(intent.intent_id, user)
        print(f"✅ Cancelled payment intent: {cancel_result['status']}")
        
        print("🎉 All payment intent service tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Payment intent service test failed: {str(e)}")
        return False

def test_payment_serializers():
    """Test the payment serializers"""
    print("\n🧪 Testing Payment Serializers...")
    
    try:
        # Test transaction serializer with mock data
        user = User.objects.filter(phone_number='+9779800000001').first()
        
        if user and user.transactions.exists():
            transaction = user.transactions.first()
            serializer = TransactionSerializer(transaction)
            print(f"✅ TransactionSerializer data: {len(serializer.data)} fields")
        else:
            print("✅ No transactions found (expected for new test)")
        
        print("🎉 All serializer tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Serializer test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Payments App Tests...\n")
    
    tests = [
        test_payment_models,
        test_wallet_service,
        test_payment_intent_service,
        test_payment_serializers
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Payments app is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())