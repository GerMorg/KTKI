FROM ghcr.io/home-assistant/base:latest
RUN apk add --no-cache python3 py3-pip && python3 -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
COPY app /app
COPY run.sh /run.sh
RUN chmod a+x /run.sh
WORKDIR /app
CMD ["/run.sh"]







