FROM ubuntu:latest AS upgrade

RUN set -xe \
    && apt update \
    && apt -y dist-upgrade \
    && rm -rf /var/lib/apt/lists/*

FROM upgrade AS venv

RUN set -xe \
    && apt update \
    && apt install -q -y --no-install-recommends \
        build-essential libssl-dev libffi-dev \
        python3-dev python3-pip python3-setuptools python3-venv \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip3 install uwsgi

COPY . /usr/src/app/

RUN cd /usr/src/app && \
    pip3 install -e .

FROM upgrade AS runtime

RUN set -xe \
    && apt update \
    && apt install -q -y --no-install-recommends \
        software-properties-common \
    && add-apt-repository ppa:libreoffice/ppa \
    && apt install -q -y --no-install-recommends \
        libreoffice-writer supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN set -xe \
    && apt update \
    && echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula boolean true" | debconf-set-selections \
    && apt install -q -y --no-install-recommends \
        curl fonts-crosextra-carlito openjdk-8-jdk-headless git gpg-agent unzip \
        openssh-client ttf-mscorefonts-installer \
        python3-dev python3-minimal python3-pip python3-setuptools python3-uno python3-wheel \
    && rm -rf /var/lib/apt/lists/*

RUN cd /tmp \
    && set -xe \
    && curl -sSLO https://github.com/jgm/pandoc/releases/download/2.9.1.1/pandoc-2.9.1.1-1-amd64.deb \
    && dpkg -i pandoc-2.9.1.1-1-amd64.deb \
    && rm pandoc-2.9.1.1-1-amd64.deb

RUN pip3 install unoconv

RUN useradd -r -d /opt/venv uwsgi

COPY --chown=uwsgi:uwsgi --from=venv /usr/src/app /usr/src/app
COPY --chown=uwsgi:uwsgi --from=venv /opt/venv /opt/venv

ADD .docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
ADD .docker/entrypoint.sh /entrypoint.sh
ADD .docker/install_features.py /usr/local/bin
ADD .docker/install_fonts.py /usr/local/bin
ADD .docker/uwsgi.ini /etc/uwsgi/uwsgi.ini

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/bin/supervisord"]

EXPOSE 8080
EXPOSE 8443
HEALTHCHECK CMD /usr/bin/curl --fail --cacert /etc/ssl/certs/uwsgi.crt --resolve 'docmaker:8443:127.0.0.1' https://docmaker:8443/health?uno || exit 1
