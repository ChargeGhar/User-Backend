from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from api.common.services.base import ServiceException
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.payments.services import RentalPaymentService
from api.user.points.models import UserPoints
from api.user.rentals.models import Rental, RentalPackage
from api.user.rentals.services import RentalDuePaymentService
from api.user.stations.models import Station, StationSlot


def _create_user_with_balances(email: str, wallet: Decimal, points: int) -> User:
    user = User.objects.create_user(email=email, username=email.split("@")[0])
    Wallet.objects.create(user=user, balance=wallet, currency="NPR", is_active=True)
    UserPoints.objects.create(user=user, current_points=points, total_points=points)
    return user


def _create_rental_with_due(
    user: User,
    amount_paid: Decimal,
    overdue_amount: Decimal,
    payment_model: str = "POSTPAID",
) -> Rental:
    station = Station.objects.create(
        station_name=f"Station-{user.username}",
        serial_number=f"SN-{user.username}",
        imei=f"IMEI-{user.username}",
        latitude=Decimal("27.700000000000000"),
        longitude=Decimal("85.300000000000000"),
        address="Test Address",
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
    package = RentalPackage.objects.create(
        name="Postpaid Due Package",
        description="Due payment package",
        duration_minutes=60,
        price=Decimal("100.00"),
        package_type="HOURLY",
        payment_model=payment_model,
        is_active=True,
    )
    return Rental.objects.create(
        user=user,
        station=station,
        slot=slot,
        package=package,
        rental_code=f"RNT-{user.username[:6]}",
        status="COMPLETED",
        payment_status="PENDING",
        due_at=slot.created_at,
        amount_paid=amount_paid,
        overdue_amount=overdue_amount,
        rental_metadata={},
    )


@pytest.mark.django_db
def test_pay_rental_due_accepts_canonical_breakdown() -> None:
    user = _create_user_with_balances("due-canonical@example.com", Decimal("20.00"), 100)
    rental = _create_rental_with_due(user, amount_paid=Decimal("20.00"), overdue_amount=Decimal("10.00"))

    txn = RentalPaymentService().pay_rental_due(
        user=user,
        rental=rental,
        payment_breakdown={
            "points_to_use": 100,
            "points_amount": Decimal("10.00"),
            "wallet_amount": Decimal("20.00"),
        },
    )

    rental.refresh_from_db()
    user.wallet.refresh_from_db()
    user.points.refresh_from_db()

    assert txn.amount == Decimal("30.00")
    assert rental.payment_status == "PAID"
    assert rental.overdue_amount == Decimal("0")
    assert user.wallet.balance == Decimal("0.00")
    assert user.points.current_points == 0


@pytest.mark.django_db
def test_pay_rental_due_accepts_legacy_breakdown_keys() -> None:
    user = _create_user_with_balances("due-legacy@example.com", Decimal("15.00"), 150)
    rental = _create_rental_with_due(user, amount_paid=Decimal("20.00"), overdue_amount=Decimal("10.00"))

    txn = RentalPaymentService().pay_rental_due(
        user=user,
        rental=rental,
        payment_breakdown={
            "points_used": 150,
            "points_amount": Decimal("15.00"),
            "wallet_used": Decimal("15.00"),
        },
    )

    rental.refresh_from_db()
    user.wallet.refresh_from_db()
    user.points.refresh_from_db()

    assert txn.amount == Decimal("30.00")
    assert rental.payment_status == "PAID"
    assert rental.overdue_amount == Decimal("0")
    assert user.wallet.balance == Decimal("0.00")
    assert user.points.current_points == 0


@pytest.mark.django_db
def test_pay_rental_due_rejects_amount_mismatch() -> None:
    user = _create_user_with_balances("due-mismatch@example.com", Decimal("50.00"), 500)
    rental = _create_rental_with_due(user, amount_paid=Decimal("20.00"), overdue_amount=Decimal("10.00"))

    with pytest.raises(ServiceException) as exc:
        RentalPaymentService().pay_rental_due(
            user=user,
            rental=rental,
            payment_breakdown={
                "points_to_use": 100,
                "points_amount": Decimal("10.00"),
                "wallet_amount": Decimal("10.00"),
            },
        )

    rental.refresh_from_db()
    assert exc.value.default_code == "payment_amount_mismatch"
    assert rental.payment_status == "PENDING"
    assert rental.overdue_amount == Decimal("10.00")


@pytest.mark.django_db
def test_pay_rental_due_rejects_when_no_due_amount() -> None:
    user = _create_user_with_balances("due-none@example.com", Decimal("50.00"), 500)
    rental = _create_rental_with_due(user, amount_paid=Decimal("0.00"), overdue_amount=Decimal("0.00"))

    with pytest.raises(ServiceException) as exc:
        RentalPaymentService().pay_rental_due(
            user=user,
            rental=rental,
            payment_breakdown={
                "points_to_use": 0,
                "points_amount": Decimal("0.00"),
                "wallet_amount": Decimal("0.00"),
            },
        )

    assert exc.value.default_code == "no_due_amount"


@pytest.mark.django_db
def test_pay_rental_due_prepaid_charges_only_overdue_amount() -> None:
    user = _create_user_with_balances("due-prepaid@example.com", Decimal("10.00"), 0)
    rental = _create_rental_with_due(
        user,
        amount_paid=Decimal("20.00"),
        overdue_amount=Decimal("10.00"),
        payment_model="PREPAID",
    )

    txn = RentalPaymentService().pay_rental_due(
        user=user,
        rental=rental,
        payment_breakdown={
            "points_to_use": 0,
            "points_amount": Decimal("0.00"),
            "wallet_amount": Decimal("10.00"),
        },
    )

    rental.refresh_from_db()
    user.wallet.refresh_from_db()

    assert txn.amount == Decimal("10.00")
    assert rental.payment_status == "PAID"
    assert rental.overdue_amount == Decimal("0")
    assert user.wallet.balance == Decimal("0.00")


@pytest.mark.django_db
def test_direct_due_prepaid_intent_amount_uses_overdue_only(monkeypatch) -> None:
    user = _create_user_with_balances("due-direct-prepaid@example.com", Decimal("0.00"), 0)
    rental = _create_rental_with_due(
        user,
        amount_paid=Decimal("20.00"),
        overdue_amount=Decimal("10.00"),
        payment_model="PREPAID",
    )
    captured: dict[str, Decimal] = {}

    class _IntentStub:
        intent_id = "intent-due-prepaid"
        amount = Decimal("0.00")
        currency = "NPR"
        gateway_url = "https://gateway.example/redirect"
        status = "PENDING"
        expires_at = rental.created_at
        intent_metadata = {"gateway": "khalti", "gateway_result": {}}

    def _capture_create_intent(*args, **kwargs):
        captured["amount"] = kwargs["amount"]
        stub = _IntentStub()
        stub.amount = kwargs["amount"]
        return stub

    monkeypatch.setattr(
        "api.user.rentals.services.rental.rental_due_service.RentalPaymentFlowService.create_topup_intent",
        _capture_create_intent,
    )

    with pytest.raises(ServiceException) as exc:
        RentalDuePaymentService().pay_rental_due(
            user=user,
            rental=rental,
            payment_mode="direct",
            payment_method_id="11111111-1111-1111-1111-111111111111",
        )

    assert exc.value.default_code == "payment_required"
    assert captured["amount"] == Decimal("10.00")
    assert exc.value.context["shortfall"] == "10.00"


@pytest.mark.django_db
def test_direct_due_postpaid_intent_amount_uses_usage_plus_overdue(monkeypatch) -> None:
    user = _create_user_with_balances("due-direct-postpaid@example.com", Decimal("0.00"), 0)
    rental = _create_rental_with_due(
        user,
        amount_paid=Decimal("20.00"),
        overdue_amount=Decimal("10.00"),
        payment_model="POSTPAID",
    )
    captured: dict[str, Decimal] = {}

    class _IntentStub:
        intent_id = "intent-due-postpaid"
        amount = Decimal("0.00")
        currency = "NPR"
        gateway_url = "https://gateway.example/redirect"
        status = "PENDING"
        expires_at = rental.created_at
        intent_metadata = {"gateway": "khalti", "gateway_result": {}}

    def _capture_create_intent(*args, **kwargs):
        captured["amount"] = kwargs["amount"]
        stub = _IntentStub()
        stub.amount = kwargs["amount"]
        return stub

    monkeypatch.setattr(
        "api.user.rentals.services.rental.rental_due_service.RentalPaymentFlowService.create_topup_intent",
        _capture_create_intent,
    )

    with pytest.raises(ServiceException) as exc:
        RentalDuePaymentService().pay_rental_due(
            user=user,
            rental=rental,
            payment_mode="direct",
            payment_method_id="11111111-1111-1111-1111-111111111111",
        )

    assert exc.value.default_code == "payment_required"
    assert captured["amount"] == Decimal("30.00")
    assert exc.value.context["shortfall"] == "30.00"


@pytest.mark.django_db
def test_due_override_keeps_callback_amount_stable_for_ongoing_overdue() -> None:
    user = _create_user_with_balances("due-override@example.com", Decimal("10.00"), 0)
    rental = _create_rental_with_due(
        user,
        amount_paid=Decimal("20.00"),
        overdue_amount=Decimal("10.00"),
        payment_model="PREPAID",
    )
    rental.status = "OVERDUE"
    rental.started_at = timezone.now() - timezone.timedelta(hours=3)
    rental.ended_at = None
    rental.due_at = timezone.now() - timezone.timedelta(hours=2)
    rental.save(update_fields=["status", "started_at", "ended_at", "due_at", "updated_at"])

    result = RentalDuePaymentService().pay_rental_due(
        user=user,
        rental=rental,
        payment_mode="wallet",
        required_due_override=Decimal("10.00"),
    )

    rental.refresh_from_db()
    user.wallet.refresh_from_db()

    assert result["amount_paid"] == 10.0
    assert rental.payment_status == "PAID"
    assert rental.overdue_amount == Decimal("0")
    assert user.wallet.balance == Decimal("0.00")
