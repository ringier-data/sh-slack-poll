# Sherlock Poll

Create native polls in Slack through slash command `/sherlock-poll`.
The current lunch polling app costs 49$/month...

## Deployment

Ubuntu 18 + Python 3.7 + gunicorn + MySQL

```bash
touch /etc/sherlock-poll.env && chmod 600 /etc/sherlock-poll.env

```
Set the credentials in the environment variable directive:
```
DJANGO_SECRET_KEY=blah-blah      <-- Django secret key, a random enough secrets
DATABASE_URL=mysql:user:pass@host:port/db      <-- (Optional) The support database schemes in URLs, refer to dj_database_url
SLACK_OAUTH_TOKEN=blahblah      <-- OAuth Access Token of Slack, starts with xoxp-
SLACK_VERIFICATION_TOKEN=blahblah  <-- "Verification Token" of Slack
```


Clone the repo into `/opt/sherlock-poll`, config nginx:

```
  ...
  location /static/ {
    root /opt/sherlock-poll/main;
  }
  location / {
    include proxy_params;
    proxy_pass http://unix:/run/gunicorn.sock;
  }
  ...
```

Create `/etc/systemd/system/gunicorn.socket`:

```
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/var/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

Create `/etc/systemd/system/gunicorn.service`:
```
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=www-data
Group=www-data
EnvironmentFile=/etc/sherlock-poll.env
WorkingDirectory=/opt/sherlock-poll
ExecStart=/usr/local/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/var/run/gunicorn.sock \
          sherlockpoll.wsgi:application

[Install]
WantedBy=multi-user.target
```
