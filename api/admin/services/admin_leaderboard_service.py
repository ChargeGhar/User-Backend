"""
Service for admin leaderboard management
============================================================

This module contains service classes for admin leaderboard operations.
Wraps social app leaderboard services with admin access.

Created: 2025-11-11
"""
from __future__ import annotations

from typing import Dict, Any

from api.common.services.base import CRUDService
from api.user.social.models import UserLeaderboard


class AdminLeaderboardService(CRUDService):
    """Service for admin leaderboard operations"""
    model = UserLeaderboard
    
    def __init__(self):
        super().__init__()
        from api.user.social.services import LeaderboardService
        self.leaderboard_service = LeaderboardService()
    
    def get_leaderboard(
        self,
        category: str = "overall",
        period: str = "all_time",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get leaderboard for admin view (extended limit)
        
        Args:
            category: Leaderboard category (overall, rentals, points, referrals, timely_returns)
            period: Time period (all_time, monthly, weekly)
            limit: Number of entries to return (default 100 for admin)
            
        Returns:
            Dict with leaderboard data
        """
        try:
            # Use core leaderboard service with admin limit
            leaderboard_data = self.leaderboard_service.get_leaderboard(
                category=category,
                period=period,
                limit=limit,
                include_user=None  # Admin doesn't need specific user position
            )
            
            return leaderboard_data
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get leaderboard")
