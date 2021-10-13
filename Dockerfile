# Mozilla PollBot server
FROM python:3.6-slim
MAINTAINER Product Delivery irc://irc.mozilla.org/#product-delivery

RUN groupadd -g 10001 pollbot && \
    useradd -M -u 10001 -g 10001 -G pollbot -d /app -s /sbin/nologin pollbot

WORKDIR /app
COPY . /app

ENV PORT 9876
ENV PYTHONBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /app

RUN buildDeps=' \
    gcc \
    libxml2-dev \
    ' && \
    # install deps
    apt-get update -y && \
    apt-get install -y --no-install-recommends $buildDeps && \
    pip install -r requirements.txt && \
    pip install -e /app && \
    # cleanup
    apt-get purge -y $buildDeps && \
    rm -rf /var/lib/apt/lists/* && \
    # allow run-tests.sh to run pip install successfully
    chmod 777 /app && \
    chmod -R 777 /app/pollbot.egg-info

USER pollbot

# Start the pollbot server
CMD pollbot
