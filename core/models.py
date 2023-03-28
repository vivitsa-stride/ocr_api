# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
import json
# Create your models here.

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class Document(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    processing_started = models.DateTimeField(null=True)
    processing_completed = models.DateTimeField(null=True)
    preprocess = models.BooleanField(default=False)
    preprocess_options = models.CharField(
        max_length=400, default=json.dumps({}))
    folder_name = models.CharField(max_length=12)
    input_file_name = models.CharField(max_length=150)
    output_file_name = models.CharField(max_length=160)
    status = models.CharField(max_length=20, default='queued')
    user = models.ForeignKey(User, null=True, related_name='documents')
