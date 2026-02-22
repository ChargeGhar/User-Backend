from django.db import models
from api.common.models import BaseModel

class ContentPage(BaseModel):
    """
    ContentPage - Static content pages like Terms, Privacy Policy, etc.
    """
    
    class PageTypeChoices(models.TextChoices):
        TERMS_OF_SERVICE = 'terms-of-service', 'Terms of Service'
        PRIVACY_POLICY = 'privacy-policy', 'Privacy Policy'
        ABOUT = 'about', 'About Us'
        CONTACT = 'contact', 'Contact Us'
        RENTING_POLICY = 'renting-policy', 'Renting Policy'
    
    page_type = models.CharField(max_length=255, choices=PageTypeChoices.choices, unique=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = "content_pages"
        verbose_name = "Content Page"
        verbose_name_plural = "Content Pages"
    
    def __str__(self):
        return self.title
