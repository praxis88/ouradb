FROM debian:bookworm-slim

WORKDIR /root

RUN apt update 
RUN apt upgrade -y 
RUN apt install -y apt-utils ca-certificates curl htop libfontconfig vim net-tools supervisor wget gnupg python3 python3-pip nodejs cron anacron procps

#Setup Supervisord
RUN mkdir -p /var/log/supervisor 
RUN mkdir -p /etc/supervisor/conf.d
COPY etc/ /etc

# Configure Oura API script
RUN pip3 install influxdb-client requests --break-system-packages
RUN chmod +x /etc/oura/oura_post_to_influxdb.py
RUN chmod +x /etc/oura/oura_query.py
RUN chmod +x /etc/cron.daily/oura_post

#Cleanup
RUN apt clean
RUN rm -rf /var/lib/apt/lists/*

CMD ["/usr/bin/supervisord"]