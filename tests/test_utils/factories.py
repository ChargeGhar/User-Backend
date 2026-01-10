import factory
from django.contrib.auth import get_user_model
from api.user.auth.models import UserProfile, UserDevice, UserKYC

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True

class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    phone = factory.Faker('phone_number')
    address = factory.Faker('address')

# Add more factories as needed for other models