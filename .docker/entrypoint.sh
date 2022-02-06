#!/bin/sh

env | grep -q -e ^DOCMAKER_INSTALL_PIP -e ^DOCMAKER_INSTALL_FEATURE -e ^DOCMAKER_INSTALL_WHEEL
if [ "$?" = "0" ]; then
    (
        . /opt/venv/bin/activate
        /usr/local/bin/install_features.py
    )
fi

env | grep -q ^DOCMAKER_INSTALL_FONT
if [ "$?" = "0" ]; then
    (
        . /opt/venv/bin/activate
        /usr/local/bin/install_fonts.py
    )
fi

if [ "$1" = "docmaker" ]; then
    shift
    . /opt/venv/bin/activate
    exec docmaker "$@"
else
    [ -n "$DOCMAKER_SSL_CERT" ] || DOCMAKER_SSL_CERT=/config/uwsgi.crt
    [ -n "$DOCMAKER_SSL_KEY" ] || DOCMAKER_SSL_KEY=/config/uwsgi.key

    if [ -e "$DOCMAKER_SSL_CERT" -a -e "$DOCMAKER_SSL_KEY" ]; then
        cp $DOCMAKER_SSL_CERT /etc/ssl/certs/uwsgi.crt
        cp $DOCMAKER_SSL_KEY /etc/ssl/certs/uwsgi.key
    elif [ ! -e "$DOCMAKER_SSL_CERT" -o ! -e "$DOCMAKER_SSL_KEY" ] ; then
        openssl genrsa --out /etc/ssl/private/uwsgi.key 2048
        openssl req -new -key /etc/ssl/private/uwsgi.key -out /tmp/uwsgi.csr -subj "/C=AU/ST=Some-State/O=Internet Widgits Pty Ltd/CN=docmaker"
        openssl x509 -req -days 365 -in /tmp/uwsgi.csr -signkey /etc/ssl/private/uwsgi.key -out /etc/ssl/certs/uwsgi.crt
        chown root:uwsgi /etc/ssl/private/uwsgi.key /etc/ssl/certs/uwsgi.crt
        chmod 0640 /etc/ssl/private/uwsgi.key /etc/ssl/certs/uwsgi.crt
        chown root:uwsgi /etc/ssl/private
        chmod 0750 /etc/ssl/private
        rm /tmp/uwsgi.csr
    fi

    exec "$@"
fi
