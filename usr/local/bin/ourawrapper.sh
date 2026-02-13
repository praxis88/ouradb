#!/bin/bash
set -a
source /etc/environment
set +a
/usr/local/bin/python3 /etc/oura/oura_post_to_influxdb.py