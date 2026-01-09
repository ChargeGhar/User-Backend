#!/usr/bin/env python
"""
Quick IoT Return Flow Tester
Usage: python test_iot_return.py <rental_code>
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from django.utils import timezone
from api.user.rentals.models import Rental
from api.user.stations.services.station_sync_service import StationSyncService
from api.user.stations.models import Station, StationSlot

def test_return(rental_code):
    print(f'\n{"="*80}')
    print(f'  🚀 IoT RETURN FLOW TEST: {rental_code}')
    print(f'{"="*80}\n')
    
    # Get rental
    rental = Rental.objects.filter(rental_code=rental_code).first()
    if not rental:
        print(f'❌ Rental {rental_code} not found!')
        return False
    
    # Reset to ACTIVE if needed
    if rental.status != 'ACTIVE':
        rental.status = 'ACTIVE'
        rental.ended_at = None
        rental.is_returned_on_time = False
        rental.return_station = None
        rental.save()
        
        rental.power_bank.status = 'RENTED'
        rental.power_bank.current_rental = rental
        rental.power_bank.current_station = None
        rental.power_bank.current_slot = None
        rental.power_bank.save()
        print(f'🔄 Reset rental to ACTIVE\n')
    
    # Show rental info
    print(f'📦 Rental: {rental.rental_code}')
    print(f'   User: {rental.user.email}')
    print(f'   Package: {rental.package.name} (NPR {rental.package.price})')
    print(f'   Started: {rental.started_at.strftime("%Y-%m-%d %H:%M")}')
    print(f'   Due: {rental.due_at.strftime("%Y-%m-%d %H:%M")}')
    
    # Check overdue
    overdue = timezone.now() - rental.due_at
    if overdue.total_seconds() > 0:
        print(f'   ⚠️  OVERDUE: {overdue.days} days, {overdue.seconds//3600} hours')
    else:
        print(f'   ✅ On time')
    
    # Get station
    station = Station.objects.filter(is_deleted=False).first()
    slot = StationSlot.objects.filter(station=station, status='AVAILABLE').first()
    
    print(f'\n🏢 Returning to: {station.station_name}')
    print(f'   Slot: #{slot.slot_number}')
    
    # User balance
    wallet = rental.user.wallet.balance
    points = rental.user.points.current_points
    print(f'\n💰 User Balance:')
    print(f'   Wallet: NPR {wallet}')
    print(f'   Points: {points}')
    
    # Call return API
    print(f'\n🔄 Processing IoT return event...')
    event_data = {
        'device': {'serial_number': station.serial_number},
        'return_event': {
            'power_bank_serial': rental.power_bank.serial_number,
            'slot_number': slot.slot_number,
            'battery_level': 85
        }
    }
    
    sync_service = StationSyncService()
    result = sync_service.process_return_event(event_data)
    
    # Show results
    rental.refresh_from_db()
    print(f'\n✅ RETURN COMPLETE!')
    print(f'\n📊 Results:')
    print(f'   Status: {rental.status}')
    print(f'   Payment: {rental.payment_status}')
    print(f'   On Time: {rental.is_returned_on_time}')
    print(f'   Package: NPR {rental.amount_paid}')
    print(f'   Late Fee: NPR {rental.overdue_amount or 0:.2f}')
    print(f'   Total: NPR {(rental.amount_paid or 0) + (rental.overdue_amount or 0):.2f}')
    
    print(f'\n🔋 Powerbank:')
    rental.power_bank.refresh_from_db()
    print(f'   Status: {rental.power_bank.status}')
    print(f'   Location: {rental.power_bank.current_station.station_name}')
    
    print(f'\n✅ Test Complete!\n')
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python test_iot_return.py <rental_code>')
        print('Example: python test_iot_return.py KMWLX6ZT')
        sys.exit(1)
    
    success = test_return(sys.argv[1])
    sys.exit(0 if success else 1)
