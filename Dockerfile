FROM python:3.12-slim-bookworm

WORKDIR /root

RUN apt-get update && apt-get install -y \
apt-utils \
ca-certificates \
curl \
libfontconfig \
gnupg \
nodejs \
cron \
procps && \
apt clean && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

#Copy Files
COPY etc/ /etc
COPY entrypoint.sh /entrypoint.sh

#Make executables
RUN chmod +x /etc/oura/oura_post_to_influxdb.py \
             /etc/cron.daily/oura_post \
             /entrypoint.sh

CMD ["/entrypoint.sh"]