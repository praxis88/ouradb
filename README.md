# Docker stack with InfluxDB and Grafana

This Docker stack is specifically intended for storing Oura sleep data in an InfluxDB2 database, and being able to easily do queries from the data using Grafana. It also has a cron job which checks for new data to upload to the database once per hour.

The Docker image is based on original work from [Samuele Bistoletti](https://github.com/samuelebistoletti) in the [Docker Image with Telegraf (StatsD), InfluxDB and Grafana](https://github.com/samuelebistoletti/docker-statsd-influxdb-grafana) and specifically on the improvements made by [Phil Hawthorne](https://github.com/philhawthorne) for persistence in [this Docker Image](https://github.com/philhawthorne/docker-influxdb-grafana). 



This fork has been significantly overhaulted to both simplify and streamline. 



## First Step: Get Personal Access Token from Oura

As the very first step, you need to get yourself a Personal Access Token (PAT) from the Oura website, here: https://cloud.ouraring.com/personal-access-tokens

Select "Create New Personal Access Token", and store the token in a safe place. Copy the oura/PAT_empty.txt file to a file named oura/PAT.txt and copy the 32 character long PAT to the new file.


## Second Step: Build and run the docker image

Now you need to build and run the image. 

```sh
docker build -t ourapython .
```

After building, ou'll want to create persistant volumes for influxdb and grafana so you dont lose data
```sh
docker volume create influxdb2
docker volume create grafana

```

## Third Step: setup stack.env

Make a stack.env to go alongside your compose file. Change any of these settings, and add your Oura Access Token

#INFLUXDB INIT VARS, these only matter when influxdb is new.
DOCKER_INFLUXDB_INIT_MODE=setup
DOCKER_INFLUXDB_INIT_USERNAME=root
DOCKER_INFLUXDB_INIT_PASSWORD=password
DOCKER_INFLUXDB_INIT_ORG=my-org
DOCKER_INFLUXDB_INIT_BUCKET=my-bucket
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=hkMQ225Qju91YaKm6wq2lo1r3-0J_dfF85j7Ff3trjCEkmCFIc-yzLEZubRcB7mL_vXYMpIilp7yrttYYRAiVA== 
#Vars for oura_post_to_influxdb.py, these are used by the script to connect to influxdb and oura cloud.
INFLUXDB_CONTAINERNAME=influxdb2
INFLUXDB_ORG=my-org
INFLUXDB_BUCKET=my-bucket
#Tokens
INFLUXDB_TOKEN=hkMQ225Qju91YaKm6wq2lo1r3-0J_dfF85j7Ff3trjCEkmCFIc-yzLEZubRcB7mL_vXYMpIilp7yrttYYRAiVA==
OURA_CLOUD_PAT=

To start the stack, run this command inside the directory where the compose and stack files live.

```sh
docker compose up -d
```

To stop the stack:

```sh
docker compose down
```


## Fourth Step: Post old data to the database

You probably want to have historic data in the database as well. You can do that by providing the start and end dates for the script oura_post_to_influxdb.py.

Example: You got your ring on 1st January 2022. You want to get historic data for the entire January 2022.

```sh
docker exec ourainjector python3 /etc/oura/oura_post_to_influxdb.py --start=2022-01-01 --end=2022-01-31
```

## Fifth Step: Create a Grafana dashboard

Next, you want to observe your data in Grafana.

Go to http://localhost:3000 in your browser, and login with username: admin, password: admin. (Remember to change these!)

You will first need to add InfluxDB as a datasource.

```
1. On the left panel, select connections
2. Select datasource, "Add data source".
3. Select InfluxDB.
4. Under Query langauge, select flux, which is compatible with influxdb2. InfluxQL does not work with influxdb2
6. Under "HTTP" > "URL", manually insert "http://2.2.2.3:8086". (Even though it looks like it already is there!)
6. Under "InfluxDB Details", set:
  - Org: my-org
  - User: root
  - Token: INFLUXDBTOKEN
  - bucket: my-bucket
6. Select "Save & Test".
```

Now, you want to construct dashboard panels

```
1. On the left, select "+" > "Create".
2. Select "Add new panel".
3. The flux language syntax takes some getting used to. The following will return all the data for given dates. You can further filter it down with more |>'s
from(bucket: "my-bucket")
  |> range(start: 2023-10-20, stop: 2023-10-22)
4. Be sure to change the time frame on the right column to something other than 6 hours.
```

Now you are ready to start creating your own panels and exploring your Oura data!
