from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, Optional

from api.common.services.base import BaseService, ServiceException
from api.user.rentals.services import RentalIssueService
from api.user.stations.services import StationIssueService


class UserIssueReportService(BaseService):
    """Aggregate station and rental issue reports for a user."""

    VALID_SCOPES = {"all", "station", "rental"}

    def __init__(self) -> None:
        self.station_issue_service = StationIssueService()
        self.rental_issue_service = RentalIssueService()

    def get_user_issue_reports(
        self,
        user,
        issue_scope: str = "all",
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get unified issue reports for the user with deterministic pagination."""
        try:
            if issue_scope not in self.VALID_SCOPES:
                raise ServiceException(
                    detail="Invalid issue_scope. Allowed values: all, station, rental",
                    code="invalid_issue_scope",
                )

            records: list[tuple[str, Any]] = []

            if issue_scope in {"all", "station"}:
                station_qs = self.station_issue_service.get_user_reported_issues_queryset(
                    user=user,
                    start_date=start_date,
                    end_date=end_date,
                )
                records.extend(("station", issue) for issue in station_qs)

            if issue_scope in {"all", "rental"}:
                rental_qs = self.rental_issue_service.get_user_reported_issues_queryset(
                    user=user,
                    start_date=start_date,
                    end_date=end_date,
                )
                records.extend(("rental", issue) for issue in rental_qs)

            records.sort(
                key=lambda row: (
                    row[1].reported_at,
                    row[1].created_at,
                    str(row[1].id),
                    row[0],
                ),
                reverse=True,
            )

            page = max(int(page), 1)
            page_size = min(max(int(page_size), 1), 50)

            total_count = len(records)
            total_pages = max(math.ceil(total_count / page_size), 1)
            current_page = min(page, total_pages)

            start_index = (current_page - 1) * page_size
            end_index = start_index + page_size
            page_records = records[start_index:end_index]

            results = [
                self._build_station_issue_row(issue)
                if scope == "station"
                else self._build_rental_issue_row(issue)
                for scope, issue in page_records
            ]

            return {
                "results": results,
                "pagination": {
                    "current_page": current_page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "page_size": page_size,
                    "has_next": current_page < total_pages,
                    "has_previous": current_page > 1,
                    "next_page": current_page + 1 if current_page < total_pages else None,
                    "previous_page": current_page - 1 if current_page > 1 else None,
                },
            }
        except ServiceException:
            raise
        except Exception as error:
            self.handle_service_error(error, "Failed to get user unified issue reports")

    def _build_station_issue_row(self, issue) -> Dict[str, Any]:
        return {
            "id": issue.id,
            "issue_scope": "station",
            "issue_type": issue.issue_type,
            "description": issue.description,
            "images": issue.images or [],
            "status": issue.status,
            "priority": issue.priority,
            "reported_at": issue.reported_at,
            "resolved_at": issue.resolved_at,
            "station": {
                "id": issue.station_id,
                "serial_number": issue.station.serial_number,
                "station_name": issue.station.station_name,
            },
            "rental": None,
        }

    def _build_rental_issue_row(self, issue) -> Dict[str, Any]:
        return {
            "id": issue.id,
            "issue_scope": "rental",
            "issue_type": issue.issue_type,
            "description": issue.description,
            "images": issue.images or [],
            "status": issue.status,
            "priority": None,
            "reported_at": issue.reported_at,
            "resolved_at": issue.resolved_at,
            "station": None,
            "rental": {
                "id": issue.rental_id,
                "rental_code": issue.rental.rental_code,
            },
        }
