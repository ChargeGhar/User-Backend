"""
Test Cases for Admin Advertisement Services
===========================================
Tests: AdminAdService
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from api.admin.services.admin_ad_service import AdminAdService
from api.user.advertisements.models import AdRequest, AdContent, AdDistribution
from api.common.services.base import ServiceException


class TestAdminAdServiceList:
    """Test AdminAdService list and detail methods"""
    
    def test_get_ad_requests_all(self, submitted_ad_request, approved_ad_request, rejected_ad_request):
        """Test getting all ad requests"""
        service = AdminAdService()
        
        ads = service.get_ad_requests()
        
        assert ads.count() >= 3
        assert submitted_ad_request in ads
        assert approved_ad_request in ads
        assert rejected_ad_request in ads
    
    def test_get_ad_requests_filter_by_status(self, submitted_ad_request, approved_ad_request):
        """Test filtering by status"""
        service = AdminAdService()
        
        # Filter SUBMITTED
        submitted_ads = service.get_ad_requests(filters={'status': 'SUBMITTED'})
        assert submitted_ad_request in submitted_ads
        assert approved_ad_request not in submitted_ads
        
        # Filter PENDING_PAYMENT
        pending_ads = service.get_ad_requests(filters={'status': 'PENDING_PAYMENT'})
        assert approved_ad_request in pending_ads
        assert submitted_ad_request not in pending_ads
    
    def test_get_ad_requests_filter_by_user(self, regular_user, submitted_ad_request):
        """Test filtering by user_id"""
        service = AdminAdService()
        
        ads = service.get_ad_requests(filters={'user_id': str(regular_user.id)})
        
        assert submitted_ad_request in ads
        for ad in ads:
            assert ad.user == regular_user
    
    def test_get_ad_requests_search(self, reviewed_ad_request):
        """Test search functionality"""
        service = AdminAdService()
        
        # Search by title
        ads = service.get_ad_requests(filters={'search': 'Test Advertisement'})
        assert reviewed_ad_request in ads
        
        # Search by full_name
        ads = service.get_ad_requests(filters={'search': 'Test Advertiser'})
        assert ads.count() >= 1
    
    def test_get_ad_request_detail(self, reviewed_ad_request):
        """Test getting single ad detail"""
        service = AdminAdService()
        
        ad = service.get_ad_request_detail(str(reviewed_ad_request.id))
        
        assert ad.id == reviewed_ad_request.id
        assert ad.title == 'Test Advertisement'
        # Verify relations loaded
        assert ad.ad_contents.count() > 0
    
    def test_get_ad_request_detail_not_found(self):
        """Test getting non-existent ad"""
        service = AdminAdService()

        with pytest.raises(ServiceException) as exc_info:
            service.get_ad_request_detail('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')

        assert exc_info.value.default_code == 'ad_not_found'


class TestAdminAdServiceReview:
    """Test AdminAdService review method"""
    
    def test_review_ad_request_success(self, admin_user, submitted_ad_request, test_stations):
        """Test successful ad review"""
        service = AdminAdService()
        
        station_ids = [str(s.id) for s in test_stations[:2]]
        
        reviewed_ad = service.review_ad_request(
            ad_id=str(submitted_ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Summer Sale Campaign',
                'description': 'Special summer discount promotion',
                'duration_days': 30,
                'admin_price': Decimal('5000.00'),
                'admin_notes': 'Approved for high-traffic locations',
                'station_ids': station_ids,
                'duration_seconds': 7,
                'display_order': 0
            }
        )
        
        # Verify ad updated
        assert reviewed_ad.status == 'UNDER_REVIEW'
        assert reviewed_ad.title == 'Summer Sale Campaign'
        assert reviewed_ad.description == 'Special summer discount promotion'
        assert reviewed_ad.duration_days == 30
        assert reviewed_ad.admin_price == Decimal('5000.00')
        assert reviewed_ad.admin_notes == 'Approved for high-traffic locations'
        assert reviewed_ad.reviewed_by == admin_user
        assert reviewed_ad.reviewed_at is not None
        
        # Verify content updated
        content = reviewed_ad.ad_contents.first()
        assert content.duration_seconds == 7
        assert content.display_order == 0
        
        # Verify distributions created
        distributions = content.ad_distributions.all()
        assert distributions.count() == 2
        distribution_station_ids = [str(d.station.id) for d in distributions]
        assert set(distribution_station_ids) == set(station_ids)
    
    def test_review_ad_request_with_start_date(self, admin_user, submitted_ad_request, test_stations):
        """Test review with start_date"""
        service = AdminAdService()
        
        start_date = date.today() + timedelta(days=5)
        
        reviewed_ad = service.review_ad_request(
            ad_id=str(submitted_ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Test Ad',
                'description': 'Test',
                'duration_days': 30,
                'admin_price': Decimal('3000.00'),
                'station_ids': [str(test_stations[0].id)],
                'start_date': start_date,
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        assert reviewed_ad.start_date == start_date
        # end_date should be calculated
        assert reviewed_ad.end_date == start_date + timedelta(days=30)
    
    def test_review_ad_request_invalid_status(self, admin_user, approved_ad_request, test_stations):
        """Test review with invalid status"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.review_ad_request(
                ad_id=str(approved_ad_request.id),
                admin_user=admin_user,
                validated_data={
                    'title': 'Test',
                    'description': 'Test',
                    'duration_days': 30,
                    'admin_price': Decimal('5000.00'),
                    'station_ids': [str(test_stations[0].id)],
                    'duration_seconds': 5,
                    'display_order': 0
                }
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_review_ad_request_invalid_stations(self, admin_user, submitted_ad_request):
        """Test review with non-existent stations"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.review_ad_request(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                validated_data={
                    'title': 'Test',
                    'description': 'Test',
                    'duration_days': 30,
                    'admin_price': Decimal('5000.00'),
                    'station_ids': ['00000000-0000-0000-0000-000000000000'],
                    'duration_seconds': 5,
                    'display_order': 0
                }
            )
        
        assert exc_info.value.default_code == 'stations_not_found'
    
    def test_review_ad_request_update_existing_review(self, admin_user, reviewed_ad_request, test_stations):
        """Test updating an already reviewed ad"""
        service = AdminAdService()
        
        # Update review
        updated_ad = service.review_ad_request(
            ad_id=str(reviewed_ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Updated Title',
                'description': 'Updated description',
                'duration_days': 45,
                'admin_price': Decimal('7000.00'),
                'admin_notes': 'Updated notes',
                'station_ids': [str(test_stations[0].id)],  # Change stations
                'duration_seconds': 10,
                'display_order': 1
            }
        )
        
        assert updated_ad.title == 'Updated Title'
        assert updated_ad.duration_days == 45
        assert updated_ad.admin_price == Decimal('7000.00')
        
        # Verify distributions updated
        content = updated_ad.ad_contents.first()
        assert content.ad_distributions.count() == 1


class TestAdminAdServiceActions:
    """Test AdminAdService perform_ad_action method"""
    
    def test_action_approve(self, admin_user, reviewed_ad_request):
        """Test APPROVE action"""
        service = AdminAdService()
        
        approved_ad = service.perform_ad_action(
            ad_id=str(reviewed_ad_request.id),
            admin_user=admin_user,
            action='approve',
            data={}
        )
        
        # Should auto-transition to PENDING_PAYMENT
        assert approved_ad.status == 'PENDING_PAYMENT'
        assert approved_ad.approved_by == admin_user
        assert approved_ad.approved_at is not None
    
    def test_action_approve_invalid_status(self, admin_user, submitted_ad_request):
        """Test APPROVE with invalid status"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                action='approve',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_action_reject(self, admin_user, submitted_ad_request):
        """Test REJECT action"""
        service = AdminAdService()
        
        rejected_ad = service.perform_ad_action(
            ad_id=str(submitted_ad_request.id),
            admin_user=admin_user,
            action='reject',
            data={'rejection_reason': 'Content violates advertising policy'}
        )
        
        assert rejected_ad.status == 'REJECTED'
        assert rejected_ad.rejection_reason == 'Content violates advertising policy'
        assert rejected_ad.reviewed_by == admin_user
        assert rejected_ad.reviewed_at is not None
    
    def test_action_reject_without_reason(self, admin_user, submitted_ad_request):
        """Test REJECT without rejection_reason"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                action='reject',
                data={}
            )
        
        assert exc_info.value.default_code == 'rejection_reason_required'
    
    def test_action_schedule(self, admin_user, paid_ad_request):
        """Test SCHEDULE action"""
        service = AdminAdService()
        
        start_date = date.today() + timedelta(days=2)
        
        scheduled_ad = service.perform_ad_action(
            ad_id=str(paid_ad_request.id),
            admin_user=admin_user,
            action='schedule',
            data={'start_date': start_date}
        )
        
        assert scheduled_ad.status == 'SCHEDULED'
        assert scheduled_ad.start_date == start_date
        # end_date should be calculated
        assert scheduled_ad.end_date == start_date + timedelta(days=scheduled_ad.duration_days)
    
    def test_action_schedule_with_end_date(self, admin_user, paid_ad_request):
        """Test SCHEDULE with explicit end_date"""
        service = AdminAdService()
        
        start_date = date.today() + timedelta(days=2)
        end_date = date.today() + timedelta(days=40)
        
        scheduled_ad = service.perform_ad_action(
            ad_id=str(paid_ad_request.id),
            admin_user=admin_user,
            action='schedule',
            data={
                'start_date': start_date,
                'end_date': end_date
            }
        )
        
        assert scheduled_ad.start_date == start_date
        assert scheduled_ad.end_date == end_date
    
    def test_action_schedule_without_start_date(self, admin_user, paid_ad_request):
        """Test SCHEDULE without start_date"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(paid_ad_request.id),
                admin_user=admin_user,
                action='schedule',
                data={}
            )
        
        assert exc_info.value.default_code == 'start_date_required'
    
    def test_action_pause(self, admin_user, running_ad_request):
        """Test PAUSE action"""
        service = AdminAdService()
        
        paused_ad = service.perform_ad_action(
            ad_id=str(running_ad_request.id),
            admin_user=admin_user,
            action='pause',
            data={}
        )
        
        assert paused_ad.status == 'PAUSED'
    
    def test_action_resume(self, admin_user, paused_ad_request):
        """Test RESUME action"""
        service = AdminAdService()
        
        resumed_ad = service.perform_ad_action(
            ad_id=str(paused_ad_request.id),
            admin_user=admin_user,
            action='resume',
            data={}
        )
        
        assert resumed_ad.status == 'RUNNING'
    
    def test_action_cancel(self, admin_user, scheduled_ad_request):
        """Test CANCEL action"""
        service = AdminAdService()
        
        cancelled_ad = service.perform_ad_action(
            ad_id=str(scheduled_ad_request.id),
            admin_user=admin_user,
            action='cancel',
            data={'reason': 'User requested cancellation'}
        )
        
        assert cancelled_ad.status == 'CANCELLED'
        assert 'User requested cancellation' in cancelled_ad.admin_notes
    
    def test_action_complete(self, admin_user, running_ad_request):
        """Test COMPLETE action"""
        service = AdminAdService()
        
        completed_ad = service.perform_ad_action(
            ad_id=str(running_ad_request.id),
            admin_user=admin_user,
            action='complete',
            data={}
        )
        
        assert completed_ad.status == 'COMPLETED'
        assert completed_ad.completed_at is not None
    
    def test_action_invalid_action(self, admin_user, submitted_ad_request):
        """Test invalid action"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                action='invalid_action',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_action'


class TestAdminAdServiceSchedule:
    """Test AdminAdService update_schedule method"""
    
    def test_update_schedule_both_dates(self, scheduled_ad_request):
        """Test updating both start and end dates"""
        service = AdminAdService()
        
        new_start = date.today() + timedelta(days=5)
        new_end = date.today() + timedelta(days=35)
        
        updated_ad = service.update_schedule(
            ad_id=str(scheduled_ad_request.id),
            validated_data={
                'start_date': new_start,
                'end_date': new_end
            }
        )
        
        assert updated_ad.start_date == new_start
        assert updated_ad.end_date == new_end
    
    def test_update_schedule_start_date_only(self, scheduled_ad_request):
        """Test updating only start_date"""
        service = AdminAdService()
        
        original_end = scheduled_ad_request.end_date
        new_start = date.today() + timedelta(days=3)
        
        updated_ad = service.update_schedule(
            ad_id=str(scheduled_ad_request.id),
            validated_data={'start_date': new_start}
        )
        
        assert updated_ad.start_date == new_start
        assert updated_ad.end_date == original_end
    
    def test_update_schedule_end_date_only(self, scheduled_ad_request):
        """Test updating only end_date"""
        service = AdminAdService()
        
        original_start = scheduled_ad_request.start_date
        new_end = date.today() + timedelta(days=40)
        
        updated_ad = service.update_schedule(
            ad_id=str(scheduled_ad_request.id),
            validated_data={'end_date': new_end}
        )
        
        assert updated_ad.start_date == original_start
        assert updated_ad.end_date == new_end
    
    def test_update_schedule_running_ad(self, running_ad_request):
        """Test updating schedule for running ad"""
        service = AdminAdService()
        
        new_end = date.today() + timedelta(days=45)
        
        updated_ad = service.update_schedule(
            ad_id=str(running_ad_request.id),
            validated_data={'end_date': new_end}
        )
        
        assert updated_ad.end_date == new_end
        assert updated_ad.status == 'RUNNING'  # Status unchanged
    
    def test_update_schedule_invalid_status(self, submitted_ad_request):
        """Test updating schedule with invalid status"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.update_schedule(
                ad_id=str(submitted_ad_request.id),
                validated_data={'start_date': date.today()}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
