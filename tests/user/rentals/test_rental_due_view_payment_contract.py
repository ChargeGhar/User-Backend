from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station, StationSlot


def _create_user(wallet_balance: Decimal, points: int) -> User:
    user = User.objects.create_user(email="dueview@example.com", username="dueview")
    Wallet.objects.create(user=user, balance=wallet_balance, currency="NPR", is_active=True)
    UserPoints.objects.create(user=user, current_points=points, total_points=points)
    return user


def _create_due_rental(
    user: User,
    amount_paid: Decimal,
    overdue_amount: Decimal,
    *,
    payment_model: str = "POSTPAID",
    status: str = "COMPLETED",
    started_at=None,
    ended_at=None,
) -> Rental:
    station = Station.objects.create(
        station_name=f"Due Station {user.username}",
        serial_number=f"DUE-SN-{user.username}",
        imei=f"DUE-IMEI-{user.username}",
        latitude=Decimal("27.700000000000000"),
        longitude=Decimal("85.300000000000000"),
        address="Due Test Address",
        total_slots=1,
        status="ONLINE",
        is_maintenance=False,
    )
    slot = StationSlot.objects.create(
        station=station,
        slot_number=1,
        status="AVAILABLE",
        battery_level=90,
    )
    package = RentalPackage.objects.create(
        name=f"Due Package {user.username}",
        description="Postpaid due package",
        duration_minutes=60,
        price=Decimal("100.00"),
        package_type="HOURLY",
        payment_model=payment_model,
        is_active=True,
    )
    due_at = timezone.now()
    if started_at is not None:
        due_at = started_at + timezone.timedelta(minutes=package.duration_minutes)

    return Rental.objects.create(
        user=user,
        station=station,
        slot=slot,
        package=package,
        rental_code=f"DUE{user.username[:6]}",
        status=status,
        payment_status="PENDING",
        started_at=started_at,
        ended_at=ended_at,
        due_at=due_at,
        amount_paid=amount_paid,
        overdue_amount=overdue_amount,
        rental_metadata={},
    )


@pytest.mark.django_db
def test_rental_due_insufficient_returns_business_block(api_client) -> None:
    user = _create_user(wallet_balance=Decimal("0.00"), points=0)
    rental = _create_due_rental(user, amount_paid=Decimal("20.00"), overdue_amount=Decimal("10.00"))
    api_client.force_authenticate(user=user)

    response = api_client.post(
        f"/api/rentals/{rental.id}/pay-due",
        {"payment_mode": "wallet"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["error"]["code"] == "payment_method_required"


@pytest.mark.django_db
def test_rental_due_success_wallet_points_split(api_client) -> None:
    user = _create_user(wallet_balance=Decimal("20.00"), points=100)
    rental = _create_due_rental(user, amount_paid=Decimal("20.00"), overdue_amount=Decimal("10.00"))
    api_client.force_authenticate(user=user)

    response = api_client.post(
        f"/api/rentals/{rental.id}/pay-due",
        {
            "payment_mode": "wallet_points",
            "wallet_amount": "20.00",
            "points_to_use": 100,
        },
        format="json",
    )

    rental.refresh_from_db()
    user.wallet.refresh_from_db()
    user.points.refresh_from_db()

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["payment_breakdown"]["points_to_use"] == 100
    assert response.data["data"]["payment_breakdown"]["wallet_amount"] == 20.0
    assert rental.payment_status == "PAID"
    assert rental.overdue_amount == Decimal("0")
    assert user.wallet.balance == Decimal("0.00")
    assert user.points.current_points == 0


@pytest.mark.django_db
def test_rental_due_direct_mode_returns_payment_required_wrapped(api_client, monkeypatch) -> None:
    user = _create_user(wallet_balance=Decimal("999.00"), points=9999)
    rental = _create_due_rental(user, amount_paid=Decimal("20.00"), overdue_amount=Decimal("10.00"))
    api_client.force_authenticate(user=user)

    class _IntentStub:
        intent_id = "intent-due-001"
        amount = Decimal("30.00")
        currency = "NPR"
        gateway_url = "https://gateway.example/redirect"
        status = "PENDING"
        expires_at = timezone.now() + timezone.timedelta(minutes=30)
        intent_metadata = {"gateway": "khalti", "gateway_result": {}}

    monkeypatch.setattr(
        "api.user.rentals.services.rental.rental_due_service.RentalPaymentFlowService.create_topup_intent",
        lambda *args, **kwargs: _IntentStub(),
    )

    response = api_client.post(
        f"/api/rentals/{rental.id}/pay-due",
        {
            "payment_mode": "direct",
            "payment_method_id": "11111111-1111-1111-1111-111111111111",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["error"]["code"] == "payment_required"
    assert response.data["data"]["error"]["context"]["payment_mode"] == "direct"


@pytest.mark.django_db
def test_rental_due_does_not_force_completed_when_not_returned(api_client) -> None:
    user = _create_user(wallet_balance=Decimal("1000.00"), points=0)
    started_at = timezone.now() - timezone.timedelta(hours=2)
    rental = _create_due_rental(
        user,
        amount_paid=Decimal("20.00"),
        overdue_amount=Decimal("10.00"),
        payment_model="PREPAID",
        status="OVERDUE",
        started_at=started_at,
        ended_at=None,
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(
        f"/api/rentals/{rental.id}/pay-due",
        {"payment_mode": "wallet"},
        format="json",
    )

    rental.refresh_from_db()

    assert response.status_code == 200
    assert response.data["success"] is True
    assert rental.payment_status == "PENDING"
    assert rental.status == "OVERDUE"
    assert rental.ended_at is None
