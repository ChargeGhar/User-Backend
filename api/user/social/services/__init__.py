"""
Social Services - Service Layer Exports
========================================

This module exports all social-related services.

Created: 2025-01-16
Part of: Social App Real-Time Achievement Update
"""

from __future__ import annotations

from .achievement_service import AchievementService
from .achievement_realtime_service import AchievementRealtimeService
from .achievement_claim_service import AchievementClaimService
from .leaderboard_service import LeaderboardService
from .social_analytics_service import SocialAnalyticsService

__all__ = [
    # Achievement Services
    "AchievementService",  # Legacy/existing achievement operations
    "AchievementRealtimeService",  # NEW: Real-time achievement calculation
    "AchievementClaimService",  # NEW: Achievement claiming operations
    # Leaderboard Service
    "LeaderboardService",  # Leaderboard operations with achievement claim support
    # Analytics Service
    "SocialAnalyticsService",  # Social analytics and statistics
]
