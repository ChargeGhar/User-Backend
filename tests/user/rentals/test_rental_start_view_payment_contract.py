from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from api.common.services.base import ServiceException
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station, StationSlot


def _create_user() -> User:
    user = User.objects.create_user(email="startview@example.com", username="startview")
    Wallet.objects.create(user=user, balance=Decimal("0.00"), currency="NPR", is_active=True)
    UserPoints.objects.create(user=user, current_points=0, total_points=0)
    return user


def _create_station() -> Station:
    return Station.objects.create(
        station_name="Test Station",
        serial_number="SN-START-VIEW",
        imei="IMEI-START-VIEW",
        latitude=Decimal("27.700000000000000"),
        longitude=Decimal("85.300000000000000"),
        address="Test Address",
        total_slots=1,
        status="ONLINE",
        is_maintenance=False,
    )


def _create_package(payment_model: str = "PREPAID") -> RentalPackage:
    return RentalPackage.objects.create(
        name=f"Test {payment_model} Package",
        description="Test package",
        duration_minutes=60,
        price=Decimal("100.00"),
        package_type="HOURLY",
        payment_model=payment_model,
        is_active=True,
    )


@pytest.mark.django_db
def test_rental_start_business_block_payment_required_wrapped(api_client, monkeypatch) -> None:
    user = _create_user()
    station = _create_station()
    package = _create_package("PREPAID")
    api_client.force_authenticate(user=user)

    def _raise_payment_required(*args, **kwargs):
        raise ServiceException(
            detail="Payment required to start rental",
            code="payment_required",
            status_code=402,
            context={"shortfall": "50.00", "payment_mode": "wallet"},
        )

    monkeypatch.setattr(
        "api.user.rentals.views.core_views.RentalService.start_rental",
        _raise_payment_required,
    )

    response = api_client.post(
        "/api/rentals/start",
        {
            "station_sn": station.serial_number,
            "package_id": str(package.id),
            "payment_mode": "wallet",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["error"]["code"] == "payment_required"
    assert response.data["data"]["error"]["context"]["payment_mode"] == "wallet"


@pytest.mark.django_db
def test_rental_start_business_block_mode_not_supported_wrapped(api_client, monkeypatch) -> None:
    user = _create_user()
    station = _create_station()
    package = _create_package("POSTPAID")
    api_client.force_authenticate(user=user)

    def _raise_mode_block(*args, **kwargs):
        raise ServiceException(
            detail="Payment mode 'points' is not supported for POSTPAID packages",
            code="payment_mode_not_supported",
            status_code=400,
            context={"payment_mode": "points", "payment_model": "POSTPAID"},
        )

    monkeypatch.setattr(
        "api.user.rentals.views.core_views.RentalService.start_rental",
        _raise_mode_block,
    )

    response = api_client.post(
        "/api/rentals/start",
        {
            "station_sn": station.serial_number,
            "package_id": str(package.id),
            "payment_mode": "points",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["error"]["code"] == "payment_mode_not_supported"


@pytest.mark.django_db
def test_rental_start_non_business_error_keeps_error_wrapper(api_client, monkeypatch) -> None:
    user = _create_user()
    station = _create_station()
    package = _create_package("PREPAID")
    api_client.force_authenticate(user=user)

    def _raise_non_business(*args, **kwargs):
        raise ServiceException(
            detail="You already have an active rental",
            code="active_rental_exists",
            status_code=400,
        )

    monkeypatch.setattr(
        "api.user.rentals.views.core_views.RentalService.start_rental",
        _raise_non_business,
    )

    response = api_client.post(
        "/api/rentals/start",
        {
            "station_sn": station.serial_number,
            "package_id": str(package.id),
            "payment_mode": "wallet",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "active_rental_exists"


@pytest.mark.django_db
def test_rental_start_success_response(api_client, monkeypatch) -> None:
    user = _create_user()
    station = _create_station()
    package = _create_package("PREPAID")
    slot = StationSlot.objects.create(
        station=station,
        slot_number=1,
        status="AVAILABLE",
        battery_level=90,
    )
    rental = Rental.objects.create(
        user=user,
        station=station,
        slot=slot,
        package=package,
        rental_code="RNTTEST01",
        status="PENDING_POPUP",
        due_at=timezone.now() + timezone.timedelta(minutes=package.duration_minutes),
        amount_paid=Decimal("0.00"),
        rental_metadata={},
    )
    api_client.force_authenticate(user=user)

    def _return_rental(*args, **kwargs):
        return rental

    monkeypatch.setattr(
        "api.user.rentals.views.core_views.RentalService.start_rental",
        _return_rental,
    )

    response = api_client.post(
        "/api/rentals/start",
        {
            "station_sn": station.serial_number,
            "package_id": str(package.id),
            "payment_mode": "wallet",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["success"] is True
    assert response.data["data"]["rental_code"] == "RNTTEST01"
