"""
Franchise User Serializers

Serializers for user search functionality.
"""

from rest_framework import serializers


class UserProfileDataSerializer(serializers.Serializer):
    """User profile data"""
    full_name = serializers.CharField(allow_null=True)
    date_of_birth = serializers.DateField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    avatar_url = serializers.URLField(allow_null=True)
    is_profile_complete = serializers.BooleanField()


class UserSearchResultSerializer(serializers.Serializer):
    """User search result with profile"""
    id = serializers.IntegerField()
    email = serializers.EmailField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    username = serializers.CharField(allow_null=True)
    profile_picture = serializers.URLField(allow_null=True)
    status = serializers.CharField()
    is_partner = serializers.BooleanField()
    profile = UserProfileDataSerializer(allow_null=True)


class UserSearchListSerializer(serializers.Serializer):
    """Paginated user search results"""
    results = UserSearchResultSerializer(many=True)
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
