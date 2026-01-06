from typing import Optional, Tuple
from api.points.models import UserPoints

class PointRepository:
    """Repository for UserPoints data operations"""
    
    @staticmethod
    def get_by_user_id(user_id: str) -> Optional[UserPoints]:
        try:
            return UserPoints.objects.get(user_id=user_id)
        except UserPoints.DoesNotExist:
            return None

    @staticmethod
    def get_or_create(user) -> Tuple[UserPoints, bool]:
        return UserPoints.objects.get_or_create(user=user)

    @staticmethod
    def create_points(user) -> UserPoints:
        return UserPoints.objects.create(user=user)
