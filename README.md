# varasto
Varastotilaussovellus

Luodaan systemd-init-palvelulle gunicorn-palvelun tiedot. Luodaan /etc/systemd/system/gunicorn.service:

[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
# gunicorn can let systemd know when it is ready
Type=notify
NotifyAccess=main
# the specific user that our service will run as
User=user
Group=user
# this user can be transiently created by systemd
# DynamicUser=true
RuntimeDirectory=varasto
WorkingDirectory=/home/user/varasto
ExecStart=/home/user/varasto/.venv/bin/gunicorn order_from_stock.wsgi
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
# if your app does not need administrative capabilities, let systemd know
# ProtectSystem=strict

[Install]
WantedBy=multi-user.target
ja seuraavanlainen tiedosto polkuun /etc/systemd/system/gunicorn.socket:

[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock
# Our service won't need permissions for the socket, since it
# inherits the file descriptor by socket activation.
# Only the nginx daemon will need access to the socket:
SocketUser=www-data
SocketGroup=www-data
# Once the user/group is correct, restrict the permissions:
SocketMode=0660

[Install]
WantedBy=sockets.target
enabloidaan luotu palvelu:

# systemctl enable --now gunicorn.socket
luodaan seuraavanlainen tiedosto polkuun /etc/nginx/sites-enabled/varasto:

server {
        listen          8000;
        server_name     127.0.0.1;
        location / {
                proxy_pass http://unix:/run/gunicorn.sock;
        }
        location /static/ {
                alias /home/user/varasto/staticfiles/;
        }

}
poistetaan nykyinen default sites-enabledista ja luodaan symbolinen linkki varastoon:

# rm /etc/nginx/sites-enabled/default
# ln -s /etc/nginx/sites-available/varasto /etc/nginx/sites-enabled/varasto
käynnistetään nginx uudestaan:

# service nginx restart
asetetaan oikeudet oikein:

chmod 711 /home/user
chmod 711 /home/user/varasto
chmod 755 /home/user/varasto/staticfiles
