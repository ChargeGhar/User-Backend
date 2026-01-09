from django.db import models
from api.common.models import BaseModel
from .station import Station


class UserStationFavorite(BaseModel):
    """
    UserStationFavorite - User's favorite stations
    """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='favorite_stations')
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='favorited_by')

    class Meta:
        db_table = "user_station_favorites"
        verbose_name = "User Station Favorite"
        verbose_name_plural = "User Station Favorites"
        unique_together = ['user', 'station']

    def __str__(self):
        return f"{self.user.username} - {self.station.station_name}"
