import requests
from datetime import datetime, timedelta
import json


def data_exists_in_influx(end_date, query_api, INFLUXDB_BUCKET):
    """Check if data already exists for this date in InfluxDB"""
    # The data is timestamped with bedtime_end, which is typically the morning
    # of the date we're querying. We need to check a wider range to catch it.
    date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Check from the previous day to the next day to catch bedtime_end times
    start = (date_obj - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z')
    stop = (date_obj + timedelta(days=1)).strftime('%Y-%m-%dT23:59:59Z')

    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: time(v: "{start}"), stop: time(v: "{stop}"))
        |> filter(fn: (r) => r["_measurement"] == "oura_measurements")
        |> filter(fn: (r) => r["_field"] == "day")
        |> filter(fn: (r) => r["_value"] == "{end_date}")
        |> limit(n: 1)
    '''
        
    try:
        result = query_api.query(query)
        for table in result:
            print(f"Table has {len(table.records)} records")
        has_data = any(len(table.records) > 0 for table in result)
        return has_data
    except Exception as e:
        print(f"Warning: Error checking InfluxDB for {end_date}: {e}")
        import traceback
        traceback.print_exc()
        return False


def fetch_data(start_date,end_date,datatype,OURA_CLOUD_PAT):
    end_date = start_date + timedelta(days=1)
    url = f"https://api.ouraring.com/v2/usercollection/{datatype}"
    headers = {"Authorization": f"Bearer {OURA_CLOUD_PAT}"}
    params = {"start_date": f"{start_date}", 'end_date': f"{end_date}"}
    response = requests.request('GET', url, headers=headers, params=params).json()

    if not response["data"]:
        print("No {} data yet for time window {}".format(datatype, start_date))
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

def get_data_one_day(start_date,end_date,OURA_CLOUD_PAT):
    sleep_data = fetch_data(start_date,end_date,'sleep',OURA_CLOUD_PAT)
    readiness_data = fetch_data(start_date,end_date,'daily_readiness',OURA_CLOUD_PAT)
    activity_data = fetch_data(start_date,end_date,'daily_activity',OURA_CLOUD_PAT)

    if sleep_data is None or readiness_data is None or activity_data is None:
        print("No complete data for {}, skipping this date".format(start_date))
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
    #print(json.dumps(post_data, indent=4))
    return post_data