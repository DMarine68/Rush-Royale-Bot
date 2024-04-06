from django.db import models

class UserSettings(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.key}: {self.value}'
