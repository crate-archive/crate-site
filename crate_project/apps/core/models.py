from django.db import models


class UserAgent(models.Model):
    raw = models.TextField(unique=True)
    short = models.CharField(max_length=150)
