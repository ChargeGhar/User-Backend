from __future__ import annotations

from decimal import Decimal

import pytest

from api.common.services.base import ServiceException
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.payments.services import PaymentCalculationService
from api.user.points.models import UserPoints
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station, StationSlot
from django.utils import timezone


def _create_user_with_balances(email: str, wallet: Decimal, points: int) -> User:
    user = User.objects.create_user(email=email, username=email.split("@")[0])
    Wallet.objects.create(user=user, balance=wallet, currency="NPR", is_active=True)
    UserPoints.objects.create(user=user, current_points=points, total_points=points)
    return user


def _create_prepaid_package(price: Decimal = Decimal("100.00")) -> RentalPackage:
    return RentalPackage.objects.create(
        name="Test PREPAID Package",
        description="Test package",
        duration_minutes=60,
        price=price,
        package_type="HOURLY",
        payment_model="PREPAID",
        is_active=True,
    )


def _create_postpaid_rental(user: User, amount_paid: Decimal, overdue_amount: Decimal) -> Rental:
    station = Station.objects.create(
        station_name=f"Calc Station {user.username}",
        serial_number=f"CALC-SN-{user.username}",
        imei=f"CALC-IMEI-{user.username}",
        latitude=Decimal("27.700000000000000"),
        longitude=Decimal("85.300000000000000"),
        address="Calculation Test Address",
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
        name=f"Postpaid Calc Package {user.username}",
        description="Postpaid payment calculation package",
        duration_minutes=60,
        price=Decimal("100.00"),
        package_type="HOURLY",
        payment_model="POSTPAID",
        is_active=True,
    )
    return Rental.objects.create(
        user=user,
        station=station,
        slot=slot,
        package=package,
        rental_code=f"CALC{user.username[:6]}",
        status="COMPLETED",
        payment_status="PENDING",
        due_at=timezone.now(),
        amount_paid=amount_paid,
        overdue_amount=overdue_amount,
        rental_metadata={},
    )


@pytest.mark.django_db
def test_wallet_mode_sufficient() -> None:
    user = _create_user_with_balances("wallet-ok@example.com", Decimal("150.00"), 0)
    package = _create_prepaid_package(Decimal("100.00"))

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="pre_payment",
        package_id=str(package.id),
        payment_mode="wallet",
    )

    assert options["is_sufficient"] is True
    assert options["shortfall"] == Decimal("0.00")
    assert options["payment_breakdown"]["wallet_amount"] == Decimal("100.00")
    assert options["payment_breakdown"]["points_to_use"] == 0


@pytest.mark.django_db
def test_wallet_mode_insufficient() -> None:
    user = _create_user_with_balances("wallet-low@example.com", Decimal("20.00"), 0)
    package = _create_prepaid_package(Decimal("100.00"))

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="pre_payment",
        package_id=str(package.id),
        payment_mode="wallet",
    )

    assert options["is_sufficient"] is False
    assert options["shortfall"] == Decimal("80.00")
    assert options["wallet_shortfall"] == Decimal("80.00")
    assert options["payment_breakdown"]["wallet_amount"] == Decimal("20.00")


@pytest.mark.django_db
def test_points_mode_sufficient() -> None:
    user = _create_user_with_balances("points-ok@example.com", Decimal("0.00"), 1200)
    package = _create_prepaid_package(Decimal("100.00"))

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="pre_payment",
        package_id=str(package.id),
        payment_mode="points",
    )

    assert options["is_sufficient"] is True
    assert options["shortfall"] == Decimal("0.00")
    assert options["payment_breakdown"]["points_to_use"] == 1000
    assert options["payment_breakdown"]["points_amount"] == Decimal("100.00")
    assert options["payment_breakdown"]["wallet_amount"] == Decimal("0.00")


@pytest.mark.django_db
def test_points_mode_insufficient() -> None:
    user = _create_user_with_balances("points-low@example.com", Decimal("0.00"), 500)
    package = _create_prepaid_package(Decimal("100.00"))

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="pre_payment",
        package_id=str(package.id),
        payment_mode="points",
    )

    assert options["is_sufficient"] is False
    assert options["shortfall"] == Decimal("50.00")
    assert options["points_shortfall"] == 500
    assert options["points_shortfall_amount"] == Decimal("50.00")
    assert options["payment_breakdown"]["points_to_use"] == 500
    assert options["payment_breakdown"]["points_amount"] == Decimal("50.00")


@pytest.mark.django_db
def test_wallet_points_mode_auto_split() -> None:
    user = _create_user_with_balances("combo-auto@example.com", Decimal("30.00"), 600)
    package = _create_prepaid_package(Decimal("100.00"))

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="pre_payment",
        package_id=str(package.id),
        payment_mode="wallet_points",
    )

    assert options["is_sufficient"] is False
    assert options["shortfall"] == Decimal("10.00")
    assert options["payment_breakdown"]["points_to_use"] == 600
    assert options["payment_breakdown"]["points_amount"] == Decimal("60.00")
    assert options["payment_breakdown"]["wallet_amount"] == Decimal("40.00")


@pytest.mark.django_db
def test_wallet_points_mode_explicit_split_sufficient() -> None:
    user = _create_user_with_balances("combo-ok@example.com", Decimal("40.00"), 600)
    package = _create_prepaid_package(Decimal("100.00"))

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="pre_payment",
        package_id=str(package.id),
        payment_mode="wallet_points",
        wallet_amount=Decimal("40.00"),
        points_to_use=600,
    )

    assert options["is_sufficient"] is True
    assert options["shortfall"] == Decimal("0.00")
    assert options["payment_breakdown"]["wallet_amount"] == Decimal("40.00")
    assert options["payment_breakdown"]["points_to_use"] == 600
    assert options["payment_breakdown"]["requested_split"]["wallet_amount"] == Decimal("40.00")


@pytest.mark.django_db
def test_wallet_points_mode_explicit_split_mismatch_raises() -> None:
    user = _create_user_with_balances("combo-mismatch@example.com", Decimal("100.00"), 500)
    package = _create_prepaid_package(Decimal("100.00"))

    with pytest.raises(ServiceException) as exc:
        PaymentCalculationService().calculate_payment_options(
            user=user,
            scenario="pre_payment",
            package_id=str(package.id),
            payment_mode="wallet_points",
            wallet_amount=Decimal("30.00"),
            points_to_use=500,
        )

    assert exc.value.default_code == "split_total_mismatch"


@pytest.mark.django_db
def test_wallet_points_mode_explicit_split_points_shortfall() -> None:
    user = _create_user_with_balances("combo-points-low@example.com", Decimal("40.00"), 600)
    package = _create_prepaid_package(Decimal("110.00"))

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="pre_payment",
        package_id=str(package.id),
        payment_mode="wallet_points",
        wallet_amount=Decimal("40.00"),
        points_to_use=700,
    )

    assert options["is_sufficient"] is False
    assert options["shortfall"] == Decimal("10.00")
    assert options["points_shortfall"] == 100
    assert options["points_shortfall_amount"] == Decimal("10.00")


@pytest.mark.django_db
def test_direct_mode_always_requires_topup() -> None:
    user = _create_user_with_balances("direct@example.com", Decimal("999.00"), 9999)
    package = _create_prepaid_package(Decimal("100.00"))

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="pre_payment",
        package_id=str(package.id),
        payment_mode="direct",
    )

    assert options["is_sufficient"] is False
    assert options["shortfall"] == Decimal("100.00")
    assert options["topup_amount_required"] == Decimal("100.00")
    assert options["payment_breakdown"]["direct_amount"] == Decimal("100.00")
    assert options["payment_breakdown"]["wallet_amount"] == Decimal("0.00")
    assert options["payment_breakdown"]["points_to_use"] == 0


@pytest.mark.django_db
def test_post_payment_amount_override_aligns_due_calculation() -> None:
    user = _create_user_with_balances("post-override@example.com", Decimal("20.00"), 100)
    rental = _create_postpaid_rental(
        user=user,
        amount_paid=Decimal("20.00"),
        overdue_amount=Decimal("10.00"),
    )

    options = PaymentCalculationService().calculate_payment_options(
        user=user,
        scenario="post_payment",
        rental_id=str(rental.id),
        amount=Decimal("30.00"),
        payment_mode="wallet_points",
        wallet_amount=Decimal("20.00"),
        points_to_use=100,
    )

    assert options["total_amount"] == Decimal("30.00")
    assert options["is_sufficient"] is True
    assert options["payment_breakdown"]["wallet_amount"] == Decimal("20.00")
    assert options["payment_breakdown"]["points_to_use"] == 100
