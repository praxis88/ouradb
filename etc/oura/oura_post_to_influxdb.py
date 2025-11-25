from datetime import datetime, timedelta
import influxdb_client, os, time
from influxdb_client import WritePrecision, InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import requests
import argparse
import json
import re

#Influxdb2 info
INFLUXDB_TOKEN = open('/etc/oura/INFLUXDBTOKEN.txt','r').read(88)
org = os.getenv('INFLUXDB_ORG', 'my-org')
pat = open('/etc/oura/PAT.txt','r').read(32)
bucket = os.getenv('INFLUXDB_BUCKET', 'my-bucket')
url = os.getenv('INFLUXDB_CONTAINERNAME', 'influxdb2')
client_ouradb = influxdb_client.InfluxDBClient(url=url, token=INFLUXDB_TOKEN, org=org)
write_api = client_ouradb.write_api(write_options=SYNCHRONOUS)
query_api = client_ouradb.query_api()

# pat = open('/etc/oura/PAT.txt','r').read(32)


def data_exists_in_influx(date_str):
    """Check if data already exists for this date in InfluxDB"""
    # Parse the date and create a range for the entire day
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    start = date_obj.strftime('%Y-%m-%dT00:00:00Z')
    stop = (date_obj + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z')
    
    query = f'''
    from(bucket: "{bucket}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn: (r) => r._measurement == "oura_measurements")
        |> limit(n: 1)
    '''
    try:
        result = query_api.query(query)
        return len(result) > 0
    except Exception as e:
        print(f"Warning: Error checking InfluxDB for {date_str}: {e}")
        return False


def fetch_data(start, end, datatype, pat_data):
    url = f"https://api.ouraring.com/v2/usercollection/{datatype}"
    headers = {"Authorization": f"Bearer {pat_data}"}
    params = {"start_date": f"{start.strftime('%Y-%m-%d')}", 'end_date': f"{end.strftime('%Y-%m-%d')}"}
    response = requests.request('GET', url, headers=headers, params=params).json()

    if not response["data"]:
        print("No {} data yet for time window {}".format(datatype, start.strftime('%Y-%m-%d')))
        return None

    resp = response["data"][0]

    #If we're looking for sleep...cycles through the items in response dictionary, finds the one that contains long_sleep, sets the active resp to that section. Otherwise naps make amess of the data.
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

def get_data_one_day(date,pat):
    end_date=datetime.strptime(date,'%Y-%m-%d')
    start_date=end_date - timedelta(days=1)
    

    sleep_data = fetch_data(start_date,end_date,'sleep',pat)
    readiness_data = fetch_data(start_date,end_date,'daily_readiness',pat)
    activity_data = fetch_data(start_date,end_date,'daily_activity',pat)
 
    if sleep_data is None or readiness_data is None or activity_data is None:
        print("No complete data for {}, skipping this date".format(date))
        return None

    # Clean out array type data
    sleep_data.pop('heart_rate', None)
    sleep_data.pop('hrv', None)
    sleep_data.pop('movement_30_sec', None)
    sleep_data.pop('sleep_phase_5_min', None)
    sleep_data.pop('low_battery_alert', None)
    sleep_data.pop('type', None)
    sleep_data.pop('readiness', None)
    readiness_data.pop('contributors', None)
    activity_data.pop('contributors', None)
    activity_data.pop('met', None)
    
    # Merge sleep and readiness data
    data = sleep_data
    data.update(readiness_data)
    data.update(activity_data)

    post_data = [{"measurement": "oura_measurements",
             "time": data['bedtime_end'],
             "fields": data
    },]
    
    return post_data


parser = argparse.ArgumentParser(description='Post Oura data to Influxdb. Omit --start and --end to process data only for today.')
parser.add_argument('--start', help="Start date of query. Format: YYYY-MM-DD")
parser.add_argument('--end', help="End date of query. Format: YYYY-MM-DD")
parser.add_argument('--force', action='store_true', help="Force reprocessing of data even if it already exists in InfluxDB")
args = parser.parse_args()

if (args.end and not args.start) or (args.start and not args.end):
    print("Provide both --start and --end dates. Omit both to process data for today.")
    exit()

date_pattern = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    
if args.start:
    if not date_pattern.match(args.start):
        print("Start date format invalid. Use format: YYYY-MM-DD")
        exit()

if args.end:
    if not date_pattern.match(args.end):
        print("End date format invalid. Use format: YYYY-MM-DD")
        exit()

only_today = False

if not args.start and not args.end:
    start_date = datetime.now()
    end_date = start_date + timedelta(days=1)
    only_today = True
else:
    start_date = datetime.strptime(args.start,'%Y-%m-%d') + timedelta(days=1)
    end_date = datetime.strptime(args.end,'%Y-%m-%d') + timedelta(days=1)


# Go through all days between start and end dates
processed_count = 0
skipped_count = 0
already_exists_count = 0

while start_date <= end_date:
    date_str = end_date.strftime('%Y-%m-%d')
    
    # Check if data already exists (unless --force flag is used or running for today only)
    if not args.force and not only_today and data_exists_in_influx(date_str):
        print("Skipped: {} (already exists in InfluxDB)".format(date_str))
        already_exists_count += 1
        skipped_count += 1
    else:
        data = get_data_one_day(date_str, pat)
        if data is not None:
            write_api.write(bucket=bucket, org=org, record=data)
            print("Processed: {}".format(date_str))
            processed_count += 1
            #print(json.dumps(data, indent=4))
        else:
            print("Skipped: {} (no data from Oura)".format(date_str))
            skipped_count += 1
        
        # Add small delay for bulk processing to avoid rate limits
        if not only_today and start_date < end_date:
            time.sleep(1)
    
    end_date = end_date - timedelta(days=1)

print("\nSummary: Processed {} days, skipped {} days ({} already existed)".format(
    processed_count, skipped_count, already_exists_count))
