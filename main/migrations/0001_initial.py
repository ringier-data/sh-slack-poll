import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Teams',
            fields=[
                ('access_token', models.CharField(max_length=255)),
                ('team_name', models.CharField(max_length=255)),
                ('team_id', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('incoming_webhook_url', models.CharField(max_length=1000)),
                ('incoming_webhook_configuration_url', models.CharField(max_length=1000)),
                ('last_changed', models.DateTimeField(auto_now=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Polls',
            fields=[
                ('timestamp', models.CharField(max_length=100, primary_key=True, serialize=False, unique=True)),
                ('channel', models.CharField(max_length=255)),
                ('question', models.CharField(max_length=1000)),
                ('options', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Votes',
            fields=[
                ('vote_id', models.AutoField(primary_key=True, serialize=False)),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.Polls')),
                ('option', models.CharField(default='', max_length=100)),
                ('users', models.CharField(default=[], max_length=255)),
            ],
        ),
    ]
