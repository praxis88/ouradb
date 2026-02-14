from datetime import datetime, timedelta, date
from influxdb_client import WritePrecision, InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import influxdb_client, os, time
import utils as utils
import requests
import argparse
import json
import re

#Load Vars
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')
INFLUXDB_CONTAINERNAME = os.getenv('INFLUXDB_CONTAINERNAME')
OURA_CLOUD_PAT = os.getenv('OURA_CLOUD_PAT')

url = f"http://{INFLUXDB_CONTAINERNAME}:8086"
client_ouradb = influxdb_client.InfluxDBClient(url=url, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client_ouradb.write_api(write_options=SYNCHRONOUS)
query_api = client_ouradb.query_api()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Fetch Oura data and write to InfluxDB')
parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)', default=None)
parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)', default=None)
args = parser.parse_args()

# Determine date range
if args.start_date and args.end_date:
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
else:
    start_date = date.today()
    end_date = start_date + timedelta(days=1)
    

# Initialize PrintTimeStamp
pts = utils.PrintTimeStamp()

# Process each date in the range
while start_date < end_date:
    # Check if data for today already exists in InfluxDB before fetching from Oura API
    if utils.data_exists_in_influx(start_date.strftime('%Y-%m-%d'), query_api, INFLUXDB_BUCKET):
        pts.write(f"Data for {start_date} already exists in InfluxDB, skipping.")
    else:
    #get the data for today
        data = utils.get_data_one_day(start_date,end_date,OURA_CLOUD_PAT)
        if data is not None:
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=data)
            pts.write("Processed: {}".format(start_date))
            #print(json.dumps(data, indent=4))
    
    start_date += timedelta(days=1)
