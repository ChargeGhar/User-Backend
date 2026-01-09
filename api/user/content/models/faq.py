from django.db import models
from api.common.models import BaseModel

class FAQ(BaseModel):
    """
    FAQ - Frequently Asked Questions
    """
    question = models.CharField(max_length=500)
    answer = models.TextField()
    category = models.CharField(max_length=255)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='created_faqs')
    updated_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='updated_faqs')
    
    class Meta:
        db_table = "faqs"
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['category', 'sort_order']
    
    def __str__(self):
        return self.question[:100]
