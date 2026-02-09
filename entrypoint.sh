#!/bin/bash
/usr/local/bin/python3 /etc/oura/oura_post_to_influxdb.py
exec /usr/sbin/cron -f