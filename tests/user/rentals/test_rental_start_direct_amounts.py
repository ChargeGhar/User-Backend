from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from api.user.rentals.services import RentalService


def _create_user(wallet_balance: Decimal) -> User:
    user = User.objects.create_user(
        email=f"direct-start-{wallet_balance}@example.com",
        username=f"direct_start_{str(wallet_balance).replace('.', '_')}",
    )
    Wallet.objects.create(user=user, balance=wallet_balance, currency="NPR", is_active=True)
    UserPoints.objects.create(user=user, current_points=0, total_points=0)
    return user


@pytest.mark.django_db
def test_direct_start_prepaid_uses_discounted_actual_price_for_topup(monkeypatch) -> None:
    service = RentalService()
    user = _create_user(Decimal("0.00"))
    package = SimpleNamespace(payment_model="PREPAID")
    captured: dict[str, Decimal] = {}

    def _capture_raise(*args, **kwargs):
        captured["topup_amount"] = args[3]
        raise RuntimeError("stop")

    monkeypatch.setattr(service, "_raise_payment_required", _capture_raise)

    with pytest.raises(RuntimeError, match="stop"):
        service._validate_and_check_payment(
            user=user,
            package=package,
            actual_price=Decimal("73.25"),
            payment_mode="direct",
            payment_method_id="11111111-1111-1111-1111-111111111111",
            station_sn="SN-DIRECT-1",
            package_id="22222222-2222-2222-2222-222222222222",
            powerbank_sn=None,
            discount=None,
            discount_amount=Decimal("26.75"),
            rental_metadata={},
            wallet_amount=None,
            points_to_use=None,
        )

    assert captured["topup_amount"] == Decimal("73.25")


@pytest.mark.django_db
def test_direct_start_postpaid_uses_min_balance_shortfall_not_package_price(monkeypatch) -> None:
    service = RentalService()
    user = _create_user(Decimal("10.00"))
    package = SimpleNamespace(payment_model="POSTPAID")
    captured: dict[str, Decimal] = {}

    def _capture_raise(*args, **kwargs):
        captured["topup_amount"] = args[3]
        captured["postpaid_min_balance"] = kwargs["postpaid_min_balance"]
        raise RuntimeError("stop")

    monkeypatch.setattr(service, "_raise_payment_required", _capture_raise)

    with pytest.raises(RuntimeError, match="stop"):
        service._validate_and_check_payment(
            user=user,
            package=package,
            actual_price=Decimal("120.00"),
            payment_mode="direct",
            payment_method_id="11111111-1111-1111-1111-111111111111",
            station_sn="SN-DIRECT-2",
            package_id="22222222-2222-2222-2222-222222222222",
            powerbank_sn=None,
            discount=None,
            discount_amount=Decimal("0.00"),
            rental_metadata={},
            wallet_amount=None,
            points_to_use=None,
        )

    assert captured["topup_amount"] == captured["postpaid_min_balance"] - Decimal("10.00")


@pytest.mark.django_db
def test_direct_start_postpaid_skips_gateway_when_min_balance_already_met(monkeypatch) -> None:
    service = RentalService()
    user = _create_user(Decimal("120.00"))
    package = SimpleNamespace(payment_model="POSTPAID")

    def _should_not_raise(*args, **kwargs):
        raise AssertionError("gateway intent should not be created when min balance is already met")

    monkeypatch.setattr(service, "_raise_payment_required", _should_not_raise)

    service._validate_and_check_payment(
        user=user,
        package=package,
        actual_price=Decimal("120.00"),
        payment_mode="direct",
        payment_method_id="11111111-1111-1111-1111-111111111111",
        station_sn="SN-DIRECT-3",
        package_id="22222222-2222-2222-2222-222222222222",
        powerbank_sn=None,
        discount=None,
        discount_amount=Decimal("0.00"),
        rental_metadata={},
        wallet_amount=None,
        points_to_use=None,
    )
