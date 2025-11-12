FROM python:3.12-alpine

WORKDIR /app

COPY *.py .
COPY requirements.txt .
COPY watermark.lua .

ENV TERM=xterm
ENV PYTHONUNBUFFERED=1

ARG TARGETPLATFORM
ARG BUILD_DATE
ARG COMMIT

RUN apk update && \
    apk add --virtual .build-deps gcc musl-dev python3-dev libc-dev linux-headers rust cargo g++ && \
    apk add git lua5.4-dev luarocks5.4 && \
    ln -s /usr/bin/luarocks-5.4 /usr/bin/luarocks && \
    luarocks install luacheck && \
    git clone "https://github.com/zeusssz/hercules-obfuscator.git" Obfuscator && \
    mv watermark.lua Obfuscator/src/modules && \
    python -m pip install --root-user-action ignore --upgrade pip && \
    pip install --root-user-action ignore --upgrade setuptools wheel && \
    pip install --root-user-action ignore -r requirements.txt && \
    apk del .build-deps && \
    find /usr/local \
    \( -type d -a -name test -o -name tests \) \
    -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
    -exec rm -rf '{}' + && \
    rm -rf /root/.cache/pip

LABEL maintainer="Discord: piko.piko.no.mi (970119359840284743)" \
      description="Hercules Bot for obfuscating lua files." \
      release=$BUILD_DATE \
      VERSION="1.4.11" \
      url="https://github.com/Serpensin/DiscordBots-Hercules"

CMD ["python3", "main.py"]
