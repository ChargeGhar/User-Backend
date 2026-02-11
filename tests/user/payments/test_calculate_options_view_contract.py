from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from django.utils import timezone

from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station, StationSlot


def _create_user_with_balances(email: str, wallet: Decimal, points: int) -> User:
    user = User.objects.create_user(email=email, username=email.split("@")[0])
    Wallet.objects.create(user=user, balance=wallet, currency="NPR", is_active=True)
    UserPoints.objects.create(user=user, current_points=points, total_points=points)
    return user


def _create_package(payment_model: str, price: Decimal) -> RentalPackage:
    return RentalPackage.objects.create(
        name=f"Calc {payment_model} Package",
        description="Payment options package",
        duration_minutes=60,
        price=price,
        package_type="HOURLY",
        payment_model=payment_model,
        is_active=True,
    )


def _create_rental(user: User, package: RentalPackage) -> Rental:
    uniq = uuid4().hex[:10].upper()
    station = Station.objects.create(
        station_name=f"Calc Station {uniq}",
        serial_number=f"CALC-{uniq}",
        imei=f"IMEI-{uniq}",
        latitude=Decimal("27.700000000000000"),
        longitude=Decimal("85.300000000000000"),
        address="Calc Address",
        total_slots=1,
        status="ONLINE",
        is_maintenance=False,
    )
    slot = StationSlot.objects.create(
        station=station,
        slot_number=1,
        status="AVAILABLE",
        battery_level=80,
    )
    started_at = timezone.now() - timezone.timedelta(minutes=60)
    ended_at = timezone.now()
    return Rental.objects.create(
        user=user,
        station=station,
        slot=slot,
        package=package,
        rental_code=f"CALC{uniq[:6]}",
        status="COMPLETED",
        payment_status="PENDING",
        started_at=started_at,
        ended_at=ended_at,
        due_at=started_at + timezone.timedelta(minutes=package.duration_minutes),
        amount_paid=Decimal("0.00"),
        overdue_amount=Decimal("0.00"),
        rental_metadata={},
    )


@pytest.mark.django_db
def test_calculate_options_requires_single_selector(api_client) -> None:
    user = _create_user_with_balances("calc-none@example.com", Decimal("100.00"), 1000)
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/payments/calculate-options",
        {"payment_mode": "wallet"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "validation_error"
    assert "selector" in response.data["error"]["context"]["validation_errors"]


@pytest.mark.django_db
def test_calculate_options_rejects_both_selectors(api_client) -> None:
    user = _create_user_with_balances("calc-both@example.com", Decimal("100.00"), 1000)
    package = _create_package("PREPAID", Decimal("50.00"))
    rental = _create_rental(user, _create_package("POSTPAID", Decimal("100.00")))
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/payments/calculate-options",
        {"package_id": str(package.id), "rental_id": str(rental.id)},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "validation_error"
    assert "selector" in response.data["error"]["context"]["validation_errors"]


@pytest.mark.django_db
def test_calculate_options_infers_prepayment_from_package_id(api_client) -> None:
    user = _create_user_with_balances("calc-pre@example.com", Decimal("30.00"), 250)
    package = _create_package("PREPAID", Decimal("50.00"))
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/payments/calculate-options",
        {"package_id": str(package.id), "payment_mode": "wallet_points"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["scenario"] == "pre_payment"
    assert response.data["data"]["payment_mode"] == "wallet_points"
    assert Decimal(str(response.data["data"]["total_amount"])) == Decimal("50.00")


@pytest.mark.django_db
def test_calculate_options_infers_postpayment_from_rental_id(api_client) -> None:
    user = _create_user_with_balances("calc-post@example.com", Decimal("200.00"), 0)
    package = _create_package("POSTPAID", Decimal("100.00"))
    rental = _create_rental(user, package)
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/payments/calculate-options",
        {"rental_id": str(rental.id), "payment_mode": "wallet"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["scenario"] == "post_payment"
    assert response.data["data"]["payment_mode"] == "wallet"
    assert Decimal(str(response.data["data"]["total_amount"])) >= Decimal("0.00")


@pytest.mark.django_db
def test_calculate_options_keeps_wallet_points_split_validation(api_client) -> None:
    user = _create_user_with_balances("calc-split@example.com", Decimal("200.00"), 500)
    package = _create_package("PREPAID", Decimal("50.00"))
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/payments/calculate-options",
        {
            "package_id": str(package.id),
            "payment_mode": "wallet",
            "wallet_amount": "10.00",
            "points_to_use": 400,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "validation_error"
    assert "wallet_points_split" in response.data["error"]["context"]["validation_errors"]


@pytest.mark.django_db
def test_calculate_options_rejects_legacy_scenario_and_amount_fields(api_client) -> None:
    user = _create_user_with_balances("calc-legacy-fields@example.com", Decimal("200.00"), 500)
    package = _create_package("PREPAID", Decimal("50.00"))
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/payments/calculate-options",
        {
            "package_id": str(package.id),
            "payment_mode": "wallet",
            "scenario": "pre_payment",
            "amount": "50.00",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "validation_error"
    assert "unsupported_fields" in response.data["error"]["context"]["validation_errors"]
