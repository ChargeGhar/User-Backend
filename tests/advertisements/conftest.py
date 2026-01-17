"""
Test Fixtures for Advertisement System
=======================================
Provides consistent test data for all advertisement tests.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from api.user.advertisements.models import AdRequest, AdContent, AdDistribution
from api.user.media.models import MediaUpload
from api.user.stations.models import Station
from api.user.payments.models import Wallet, Transaction

User = get_user_model()


@pytest.fixture
def regular_user(db):
    """Create a regular user for testing"""
    user = User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        phone_number='+977-9841234567',
        is_active=True
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing"""
    admin = User.objects.create_user(
        username='admin',
        email='admin@example.com',
        phone_number='+977-9841111111',
        is_staff=True,
        is_superuser=True,
        is_active=True
    )
    return admin


@pytest.fixture
def user_with_wallet(regular_user):
    """Create user with wallet and sufficient balance"""
    wallet, created = Wallet.objects.get_or_create(
        user=regular_user,
        defaults={
            'balance': Decimal('10000.00'),
            'currency': 'NPR',
            'is_active': True
        }
    )
    if not created:
        wallet.balance = Decimal('10000.00')
        wallet.save()
    return regular_user


@pytest.fixture
def user_with_low_balance(regular_user):
    """Create user with insufficient wallet balance"""
    wallet, created = Wallet.objects.get_or_create(
        user=regular_user,
        defaults={
            'balance': Decimal('100.00'),
            'currency': 'NPR',
            'is_active': True
        }
    )
    if not created:
        wallet.balance = Decimal('100.00')
        wallet.save()
    return regular_user


@pytest.fixture
def image_media(regular_user):
    """Create an IMAGE media upload"""
    media = MediaUpload.objects.create(
        file_url='https://example.com/test-image.jpg',
        file_type='IMAGE',
        original_name='test-image.jpg',
        file_size=1024000,
        uploaded_by=regular_user,
        cloud_provider='cloudinary',
        public_id='test_image_123'
    )
    return media


@pytest.fixture
def video_media(regular_user):
    """Create a VIDEO media upload"""
    media = MediaUpload.objects.create(
        file_url='https://example.com/test-video.mp4',
        file_type='VIDEO',
        original_name='test-video.mp4',
        file_size=5120000,
        uploaded_by=regular_user,
        cloud_provider='cloudinary',
        public_id='test_video_456'
    )
    return media


@pytest.fixture
def document_media(regular_user):
    """Create a DOCUMENT media upload (invalid for ads)"""
    media = MediaUpload.objects.create(
        file_url='https://example.com/test-doc.pdf',
        file_type='DOCUMENT',
        original_name='test-doc.pdf',
        file_size=512000,
        uploaded_by=regular_user,
        cloud_provider='cloudinary',
        public_id='test_doc_789'
    )
    return media


@pytest.fixture
def test_stations(db):
    """Create test stations"""
    stations = []
    for i in range(3):
        station = Station.objects.create(
            station_name=f'Test Station {i+1}',
            serial_number=f'TEST-SN-{i+1:03d}',
            imei=f'TEST-IMEI-{i+1:015d}',
            address=f'Test Address {i+1}',
            latitude=27.7172 + (i * 0.01),
            longitude=85.3240 + (i * 0.01),
            status='ONLINE',
            is_maintenance=False,
            total_slots=10
        )
        stations.append(station)
    return stations


@pytest.fixture
def submitted_ad_request(regular_user, image_media):
    """Create a SUBMITTED ad request"""
    ad_request = AdRequest.objects.create(
        user=regular_user,
        full_name='Test Advertiser',
        contact_number='+977-9841234567',
        status='SUBMITTED',
        submitted_at=timezone.now()
    )
    
    AdContent.objects.create(
        ad_request=ad_request,
        media_upload=image_media,
        content_type='IMAGE',
        is_active=True,
        duration_seconds=5,
        display_order=0
    )
    
    return ad_request


@pytest.fixture
def reviewed_ad_request(regular_user, image_media, admin_user, test_stations):
    """Create a UNDER_REVIEW ad request with pricing and stations"""
    ad_request = AdRequest.objects.create(
        user=regular_user,
        full_name='Test Advertiser',
        contact_number='+977-9841234567',
        status='UNDER_REVIEW',
        reviewed_by=admin_user,
        reviewed_at=timezone.now(),
        title='Test Advertisement',
        description='Test description for advertisement',
        duration_days=30,
        admin_price=Decimal('5000.00'),
        admin_notes='Approved for testing',
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=31),
        submitted_at=timezone.now()
    )

    AdContent.objects.create(
        ad_request=ad_request,
        media_upload=image_media,
        content_type='IMAGE',
        is_active=True,
        duration_seconds=7,
        display_order=0
    )

    # Create distributions
    content = ad_request.ad_contents.first()
    for station in test_stations[:2]:  # Use first 2 stations
        AdDistribution.objects.create(
            ad_content=content,
            station=station
        )

    return ad_request


@pytest.fixture
def approved_ad_request(regular_user, image_media, admin_user, test_stations):
    """Create an APPROVED ad request (auto-transitioned to PENDING_PAYMENT)"""
    ad_request = AdRequest.objects.create(
        user=regular_user,
        full_name='Test Advertiser',
        contact_number='+977-9841234567',
        status='PENDING_PAYMENT',
        approved_by=admin_user,
        approved_at=timezone.now(),
        title='Test Advertisement',
        description='Test description for advertisement',
        duration_days=30,
        admin_price=Decimal('5000.00'),
        admin_notes='Approved for testing',
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=31),
        submitted_at=timezone.now(),
        reviewed_by=admin_user,
        reviewed_at=timezone.now()
    )

    AdContent.objects.create(
        ad_request=ad_request,
        media_upload=image_media,
        content_type='IMAGE',
        is_active=True,
        duration_seconds=7,
        display_order=0
    )

    content = ad_request.ad_contents.first()
    for station in test_stations[:2]:
        AdDistribution.objects.create(
            ad_content=content,
            station=station
        )

    return ad_request


@pytest.fixture
def paid_ad_request(approved_ad_request, user_with_wallet):
    """Create a PAID ad request with transaction"""
    ad_request = approved_ad_request
    
    # Create transaction
    txn = Transaction.objects.create(
        user=user_with_wallet,
        transaction_id=f'TXN{timezone.now().strftime("%Y%m%d%H%M%S")}TEST',
        transaction_type='ADVERTISEMENT',
        amount=ad_request.admin_price,
        currency='NPR',
        status='SUCCESS',
        payment_method_type='WALLET'
    )
    
    ad_request.transaction = txn
    ad_request.paid_at = timezone.now()
    ad_request.status = 'PAID'
    ad_request.save()
    
    return ad_request


@pytest.fixture
def scheduled_ad_request(paid_ad_request):
    """Create a SCHEDULED ad request"""
    ad_request = paid_ad_request
    ad_request.status = 'SCHEDULED'
    ad_request.start_date = date.today() + timedelta(days=1)
    ad_request.end_date = date.today() + timedelta(days=31)
    ad_request.save()
    return ad_request


@pytest.fixture
def running_ad_request(scheduled_ad_request):
    """Create a RUNNING ad request"""
    ad_request = scheduled_ad_request
    ad_request.status = 'RUNNING'
    ad_request.start_date = date.today()
    ad_request.end_date = date.today() + timedelta(days=30)
    ad_request.save()
    return ad_request


@pytest.fixture
def paused_ad_request(running_ad_request):
    """Create a PAUSED ad request"""
    ad_request = running_ad_request
    ad_request.status = 'PAUSED'
    ad_request.save()
    return ad_request


@pytest.fixture
def completed_ad_request(running_ad_request):
    """Create a COMPLETED ad request"""
    ad_request = running_ad_request
    ad_request.status = 'COMPLETED'
    ad_request.completed_at = timezone.now()
    ad_request.end_date = date.today() - timedelta(days=1)
    ad_request.save()
    return ad_request


@pytest.fixture
def rejected_ad_request(regular_user, image_media, admin_user):
    """Create a REJECTED ad request"""
    ad_request = AdRequest.objects.create(
        user=regular_user,
        full_name='Test Advertiser',
        contact_number='+977-9841234567',
        status='REJECTED',
        rejection_reason='Content violates policy',
        reviewed_by=admin_user,
        reviewed_at=timezone.now(),
        submitted_at=timezone.now()
    )

    AdContent.objects.create(
        ad_request=ad_request,
        media_upload=image_media,
        content_type='IMAGE',
        is_active=True,
        duration_seconds=5,
        display_order=0
    )

    return ad_request


@pytest.fixture
def cancelled_ad_request(scheduled_ad_request):
    """Create a CANCELLED ad request"""
    ad_request = scheduled_ad_request
    ad_request.status = 'CANCELLED'
    ad_request.admin_notes += '\nCancellation reason: User requested cancellation'
    ad_request.save()
    return ad_request
