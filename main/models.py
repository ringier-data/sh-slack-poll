import django
from django.db import models


class Teams(models.Model):
    access_token = models.CharField(max_length=1000)
    team_name = models.CharField(max_length=1000)
    team_id = models.CharField(primary_key=True, max_length=1000, serialize=False)
    incoming_webhook_url = models.CharField(max_length=1000)
    incoming_webhook_configuration_url = models.CharField(max_length=1000)
    last_changed = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)


class Polls(models.Model):
    timestamp = models.CharField(max_length=100, primary_key=True, serialize=False, unique=True)
    channel = models.CharField(max_length=1000)
    question = models.CharField(max_length=1000)
    options = models.CharField(max_length=1000)


class Votes(models.Model):
    vote_id = models.AutoField(primary_key=True, serialize=False)
    poll = models.ForeignKey(Polls, on_delete=django.db.models.deletion.CASCADE)
    option = models.CharField(default='', max_length=100)
    users = models.CharField(default=[], max_length=1000)
