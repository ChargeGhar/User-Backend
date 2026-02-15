from __future__ import annotations

from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def rental_flow_tester_view(request):
    """Temporary UI for exercising rental start/pay-due/cancel flows via existing APIs."""
    return render(request, "internal/rental_flow_tester.html")

