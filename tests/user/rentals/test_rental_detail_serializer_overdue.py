from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from django.utils import timezone

from api.user.auth.models import User
from api.user.rentals.models import Rental, RentalPackage
from api.user.rentals.serializers import RentalDetailSerializer
from api.user.stations.models import Station, StationSlot


def _create_user() -> User:
    suffix = uuid4().hex[:8]
    return User.objects.create_user(
        email=f"serializer_overdue_{suffix}@example.com",
        username=f"serializer_overdue_{suffix}",
    )


def _create_station_and_slot(suffix: str) -> tuple[Station, StationSlot]:
    station = Station.objects.create(
        station_name=f"Serializer Station {suffix}",
        serial_number=f"SER-{suffix}",
        imei=f"IMEI-{suffix}",
        latitude=Decimal("27.700000000000000"),
        longitude=Decimal("85.300000000000000"),
        address="Serializer Test Address",
        total_slots=1,
        status="ONLINE",
        is_maintenance=False,
    )
    slot = StationSlot.objects.create(
        station=station,
        slot_number=1,
        status="AVAILABLE",
        battery_level=95,
    )
    return station, slot


def _create_package(suffix: str) -> RentalPackage:
    return RentalPackage.objects.create(
        name=f"Serializer Package {suffix}",
        description="Serializer test package",
        duration_minutes=60,
        price=Decimal("100.00"),
        package_type="HOURLY",
        payment_model="PREPAID",
        is_active=True,
    )


@pytest.mark.django_db
def test_completed_late_rental_sets_is_overdue_true() -> None:
    suffix = uuid4().hex[:8]
    user = _create_user()
    station, slot = _create_station_and_slot(suffix)
    package = _create_package(suffix)

    started_at = timezone.now() - timezone.timedelta(hours=2)
    due_at = started_at + timezone.timedelta(minutes=package.duration_minutes)
    ended_at = due_at + timezone.timedelta(minutes=30)

    rental = Rental.objects.create(
        user=user,
        station=station,
        return_station=station,
        slot=slot,
        package=package,
        rental_code=f"LATE{suffix[:6].upper()}",
        status="COMPLETED",
        payment_status="PENDING",
        started_at=started_at,
        ended_at=ended_at,
        due_at=due_at,
        amount_paid=Decimal("100.00"),
        overdue_amount=Decimal("20.00"),
        is_returned_on_time=False,
        rental_metadata={},
    )

    data = RentalDetailSerializer(rental).data

    assert data["minutes_overdue"] == 30
    assert data["is_overdue"] is True


@pytest.mark.django_db
def test_completed_on_time_rental_sets_is_overdue_false() -> None:
    suffix = uuid4().hex[:8]
    user = _create_user()
    station, slot = _create_station_and_slot(suffix)
    package = _create_package(suffix)

    started_at = timezone.now() - timezone.timedelta(hours=2)
    due_at = started_at + timezone.timedelta(minutes=package.duration_minutes)
    ended_at = due_at - timezone.timedelta(minutes=1)

    rental = Rental.objects.create(
        user=user,
        station=station,
        return_station=station,
        slot=slot,
        package=package,
        rental_code=f"ONTM{suffix[:6].upper()}",
        status="COMPLETED",
        payment_status="PAID",
        started_at=started_at,
        ended_at=ended_at,
        due_at=due_at,
        amount_paid=Decimal("100.00"),
        overdue_amount=Decimal("0.00"),
        is_returned_on_time=True,
        rental_metadata={},
    )

    data = RentalDetailSerializer(rental).data

    assert data["minutes_overdue"] == 0
    assert data["is_overdue"] is False
