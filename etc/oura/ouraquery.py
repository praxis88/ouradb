import requests
from datetime import datetime, timedelta
import json
from datetime import datetime, timedelta, date
from influxdb_client import WritePrecision, InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import influxdb_client, os, time
import utils as utils
import requests
import argparse
import json
import re

OURA_CLOUD_PAT = os.getenv('OURA_CLOUD_PAT')
end_date = date.today() + timedelta(days=1)
start_date = date.today()

def get_data(start_date,end_date,OURA_CLOUD_PAT,datatype):
    url = f"https://api.ouraring.com/v2/usercollection/{datatype}"
    headers = {"Authorization": f"Bearer {OURA_CLOUD_PAT}"}
    params = {"start_date": f"{start_date}", 'end_date': f"{end_date}"}
    response = requests.request('GET', url, headers=headers, params=params).json()
    resp = response["data"][0]

    indexstart = 0
    indexceiling = len(response["data"]) - 1
    if datatype == 'sleep':
        while indexstart <= indexceiling:
            resp2 = response["data"][indexstart]
            for k, v in resp2.items():
                if v == "long_sleep":
                    resp = resp2
            indexstart+= 1

    #Adds the contributors section at level 0 of our readiness json. Includes stats like hrv and sleep balance
    if datatype == 'daily_readiness':
        resp2 = response["data"][0]["contributors"]
        resp.pop('contributors', None)
        resp.update(resp2)

    # All data should be consistent in influxdb, so turn ints to floats
    resp = {k:float(v) if type(v) == int else v for k,v in resp.items()}
    return resp

def prune(slee_data, readiness_data, activity_data):
    sleep_data.pop('heart_rate', None)
    sleep_data.pop('hrv', None)
    sleep_data.pop('movement_30_sec', None)
    sleep_data.pop('sleep_phase_5_min', None)
    sleep_data.pop('sleep_phase_30_sec', None)
    sleep_data.pop('low_battery_alert', None)
    sleep_data.pop('type', None)
    sleep_data.pop('readiness', None)
    readiness_data.pop('contributors', None)
    activity_data.pop('contributors', None)
    activity_data.pop('met', None)

    data = sleep_data
    data.update(readiness_data)
    data.update(activity_data)
    return data


sleep_data = get_data(start_date,end_date,OURA_CLOUD_PAT, datatype='sleep')
readiness_data = get_data(start_date,end_date,OURA_CLOUD_PAT, datatype='daily_readiness')
activity_data = get_data(start_date,end_date,OURA_CLOUD_PAT, datatype='daily_activity')


data = prune(sleep_data, readiness_data, activity_data)


print(json.dumps(data, indent=4))