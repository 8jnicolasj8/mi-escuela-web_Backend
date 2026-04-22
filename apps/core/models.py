""" apps/core/models.py """
from django.db import models

class SingletonModel(models.Model):
    """Modelo base para configuración global del sistema"""
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj