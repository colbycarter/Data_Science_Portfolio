# Project 3 Setup
## Author: Colby Carter


## Situation:
- You're a data scientist at a game development company.  
- Your latest mobile game has two events you're interested in tracking: 
- `buy a sword` & `join guild`...
- Each has metadata

## Project 3 Task
- Instrument your API server to catch and analyze these two
event types.
- This task will be spread out over the last four assignments (9-12).

---

# Assignment 12

**Summary**: In this assignment, we create a simple game using a web API and log the events of the game to our kafka topic; consume them for viewing in a Spark dataframe; see that we can store, overwrite and filter our data as Hadoop parque files; and lastly pull our parquet files into Jupyter notebook.

## We begin by creating our docker cluster file with zookeeper, kafka and mids containers and spinning up the cluster.

```
cp ~/w205/course-content/12-Storing-Data-III/docker-compose.yml .
docker-compose up -d
```

## We also copy in our python scripts for extracting events to pyspark.

```
cp ~/w205/course-content/11-Storing-Data-III/extract_events.py .
cp ~/w205/course-content/11-Storing-Data-III/separate_events.py .
cp ~/w205/course-content/11-Storing-Data-III/transform_events.py .
```


## Next we create our kafka topic which we call "events".

```
docker-compose exec kafka kafka-topics --create --topic events --partitions 1 --replication-factor 1 --if-not-exists --zookeeper zookeeper:32181
```

## Separately in other windows, we spin up our Kafka logs to track publishing and our Cloudera Hadoop file system.

```
docker-compose logs -f cloudera
docker-compose exec cloudera hadoop fs -ls /tmp/
docker-compose logs -f kafka
```


## We next create a short python program called `game_api.py` using the `flask` library to function as our game API, where the user can buy a sword or join a guild.

```
#!/usr/bin/env python
from flask import Flask
app = Flask(__name__)

@app.route("/")
def default_response():
    return "\nThis is the default response!\n"

@app.route("/purchase_a_sword")
def purchase_sword():
    # business logic to purchase sword
    return "\nSword Purchased!\n"

@app.route("/join_guild")
def join_guild():
    return "\nJoined guild!\n"

```

## In a new window, we exec into our mids environment to interact with our API.

```
docker-compose exec mids env FLASK_APP=/w205/assignment-11-colbycarter/game_api.py flask run
```

## Now we can make API calls using the above suffixes to the URL.

```
docker-compose exec mids curl http://localhost:5000/purchase_a_sword
```

**Message**: Sword Purchased!

```
docker-compose exec mids curl http://localhost:5000/join_guild
```

**Message**: Joined guild!


## We'll now add the library `KafkaProducer` to our python script in order to log each event to our kafka topic.

```
#!/usr/bin/env python
from kafka import KafkaProducer
from flask import Flask
app = Flask(__name__)
event_logger = KafkaProducer(bootstrap_servers='kafka:29092')
events_topic = 'events'

@app.route("/")
def default_response():
    event_logger.send(events_topic, 'default'.encode())
    return "\nThis is the default response!\n"

@app.route("/purchase_a_sword")
def purchase_sword():
    # business logic to purchase sword
    # log event to kafka
    event_logger.send(events_topic, 'purchased_sword'.encode())
    return "\nSword Purchased!\n"

@app.route("/join_guild")
def join_guild():
    # business logic to join guild
    # log event to kafka
    event_logger.send(events_topic, 'joined_guild'.encode())
    return "\nJoined Guild!\n"

```

## We'll again access our API.

```
docker-compose exec mids env FLASK_APP=/w205/assignment-11-colbycarter/game_api.py flask run
```

## After exec-ing into our website several times to purchase swords and join the guild, we can access what sample events were published to kafka.

```
docker-compose exec mids curl http://localhost:5000/purchase_a_sword
docker-compose exec mids curl http://localhost:5000/join_guild
...
docker-compose exec mids bash -c "kafkacat -C -b kafka:29092 -t events -o beginning -e"
```

```
purchased_sword
purchased_sword
purchased_sword
joined_guild
purchased_sword
joined_guild
default
joined_guild
% Reached end of topic events [0] at offset 9: exiting
```


## Now we would like to log  more detailed information to Kafka from our events using Flask's `request` module.

```
#!/usr/bin/env python
import json
from kafka import KafkaProducer
from flask import Flask, request

app = Flask(__name__)
producer = KafkaProducer(bootstrap_servers='kafka:29092')


def log_to_kafka(topic, event):
    event.update(request.headers)
    producer.send(topic, json.dumps(event).encode())


@app.route("/")
def default_response():
    default_event = {'event_type': 'default'}
    log_to_kafka('events', default_event)
    return "\nThis is the default response!\n"


@app.route("/purchase_a_sword")
def purchase_a_sword():
    purchase_sword_event = {'event_type': 'purchase_sword'}
    log_to_kafka('events', purchase_sword_event)
    return "\nSword Purchased!\n"

@app.route("/join_guild")
def join_guild():
    # business logic to join guild
    # log event to kafka
    join_guild_event = {'event_type': 'join_guild'}
    log_to_kafka('events', join_guild_event)
    return "\nJoined Guild!\n"
```


## We will again exec into our mids container using our new API environment from `game_api_with_extended_json_events.py`.

```
docker-compose exec mids \
  env FLASK_APP=/w205/assignment-11-colbycarter/game_api_with_extended_json_events.py \
  flask run --host 0.0.0.0
```


## We then can use the kafkacat utility in a new window to subscribe to these events with additional event detail.

```
docker-compose exec mids \
  kafkacat -C -b kafka:29092 -t events -o beginning -e
```

## ...as well as by running a pyspark shell.

```
docker-compose exec spark pyspark
```

## We then read in the data by subscribing to our kafka events and storing in an object of the class Spark.

```
raw_events = spark \
  .read \
  .format("kafka") \
  .option("kafka.bootstrap.servers", "kafka:29092") \
  .option("subscribe","events") \
  .option("startingOffsets", "earliest") \
  .option("endingOffsets", "latest") \
  .load()
```

## We can take a preliminary view of the events' data structure and view the values represented in hexidecimal.

```
raw_events.cache()
raw_events.show()
```

## We clean this structure up by casting the raw event values as readable strings.

```
events = raw_events.select(raw_events.value.cast('string'))
```

## Then using the json library, we extract those string values to a dataframe that we can process in Spark.

```
import json
extracted_events = events.rdd.map(lambda x: json.loads(x.value)).toDF()
```

## We now have a readable, structured dataframe that contains host and user information, as well as the type of event requested.


|Accept|          Host| User-Agent|    event_type|
|------|--------------|-----------|--------------|
|   */*|localhost:5000|curl/7.47.0|    join_guild|
|   */*|localhost:5000|curl/7.47.0|    join_guild|
|   */*|localhost:5000|curl/7.47.0|    join_guild|
|   */*|localhost:5000|curl/7.47.0|purchase_sword|
|   */*|localhost:5000|curl/7.47.0|purchase_sword|
|   */*|localhost:5000|curl/7.47.0|    join_guild|
|   */*|localhost:5000|curl/7.47.0|purchase_sword|
|   */*|localhost:5000|curl/7.47.0|       default|
|   */*|localhost:5000|curl/7.47.0|       default|
|   */*|localhost:5000|curl/7.47.0|purchase_sword|
|   */*|localhost:5000|curl/7.47.0|    join_guild|




## Now, instead of using pyspark, we will use spark-submit from the pyspark.sql package in `extract_events.py`.

```
#!/usr/bin/env python
"""Extract events from kafka and write them to hdfs
"""
import json
from pyspark.sql import SparkSession


def main():
    """main
    """
    spark = SparkSession \
        .builder \
        .appName("ExtractEventsJob") \
        .getOrCreate()

    raw_events = spark \
        .read \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", "events") \
        .option("startingOffsets", "earliest") \
        .option("endingOffsets", "latest") \
        .load()

    events = raw_events.select(raw_events.value.cast('string'))
    extracted_events = events.rdd.map(lambda x: json.loads(x.value)).toDF()

    extracted_events \
        .write \
        .parquet("/tmp/extracted_events")


if __name__ == "__main__":
    main()

```

Exec into spark container:

```
docker-compose exec spark spark-submit /w205/assignment-11-colbycarter/extract_events.py
```

## By checking our Cloudera Hadoop temporary folder, we see that we have stored our events as temporary files.

```
docker-compose exec cloudera hadoop fs -ls /tmp/
```

## This produced a temporary `/tmp/extracted_events` of parque files.


## Next, we can transform our events with some innocuous name changes to overwrite the parque files in our temporary storage.

```
#!/usr/bin/env python
"""Extract events from kafka, transform, and write to hdfs
"""
import json
from pyspark.sql import SparkSession, Row
from pyspark.sql.functions import udf


@udf('string')
def munge_event(event_as_json):
    event = json.loads(event_as_json)
    event['Host'] = "moe" # silly change to show it works
    event['Cache-Control'] = "no-cache"
    return json.dumps(event)


def main():
    """main
    """
    spark = SparkSession \
        .builder \
        .appName("ExtractEventsJob") \
        .getOrCreate()

    raw_events = spark \
        .read \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", "events") \
        .option("startingOffsets", "earliest") \
        .option("endingOffsets", "latest") \
        .load()

    munged_events = raw_events \
        .select(raw_events.value.cast('string').alias('raw'),
                raw_events.timestamp.cast('string')) \
        .withColumn('munged', munge_event('raw'))
    munged_events.show()

    extracted_events = munged_events \
        .rdd \
        .map(lambda r: Row(timestamp=r.timestamp, **json.loads(r.munged))) \
        .toDF()
    extracted_events.show()

    extracted_events \
        .write \
        .mode("overwrite") \
        .parquet("/tmp/extracted_events")


if __name__ == "__main__":
    main()

```

## We run another spark-submit with the new file.

```
docker-compose exec spark spark-submit /w205/assignment-11-colbycarter/transform_events.py
```

## We see from our show() method that we changed the 'Cache-Control' and 'Host' columns for all rows.


|Accept|Cache-Control|Host| User-Agent|    event_type|           timestamp|
|------|-------------|----|-----------|--------------|--------------------|
|   */*|     no-cache| moe|curl/7.47.0|purchase_sword|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|purchase_sword|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|purchase_sword|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|purchase_sword|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|    join_guild|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|    join_guild|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|    join_guild|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|    join_guild|2018-07-29 18:31:...|



## Lastly, we show that we can separate our event types, adding a filter for when the user publishes a "join_guild".

```
#!/usr/bin/env python
"""Extract events from kafka and write them to hdfs
"""
import json
from pyspark.sql import SparkSession, Row
from pyspark.sql.functions import udf


@udf('string')
def munge_event(event_as_json):
    event = json.loads(event_as_json)
    event['Host'] = "moe" # silly change to show it works
    event['Cache-Control'] = "no-cache"
    return json.dumps(event)


def main():
    """main
    """
    spark = SparkSession \
        .builder \
        .appName("ExtractEventsJob") \
        .getOrCreate()

    raw_events = spark \
        .read \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", "events") \
        .option("startingOffsets", "earliest") \
        .option("endingOffsets", "latest") \
        .load()

    munged_events = raw_events \
        .select(raw_events.value.cast('string').alias('raw'),
                raw_events.timestamp.cast('string')) \
        .withColumn('munged', munge_event('raw'))

    extracted_events = munged_events \
        .rdd \
        .map(lambda r: Row(timestamp=r.timestamp, **json.loads(r.munged))) \
        .toDF()

    sword_purchases = extracted_events \
        .filter(extracted_events.event_type == 'purchase_sword')
    sword_purchases.show()
    # sword_purchases \
        # .write \
        # .mode("overwrite") \
        # .parquet("/tmp/sword_purchases")

    # add separation for guilds joined
    joined_guilds = extracted_events.filter(extracted_events.event_type == 'join_guild')
    joined_guilds.show()

    default_hits = extracted_events \
        .filter(extracted_events.event_type == 'default')
    default_hits.show()
    # default_hits \
        # .write \
        # .mode("overwrite") \
        # .parquet("/tmp/default_hits")


if __name__ == "__main__":
    main()

```


## We use spark-submit to separate the events.

```
docker-compose exec spark spark-submit /w205/assignment-12-colbycarter/separate_events.py
```

## Spark now shows us the two outputs of events separately because of our filters:


|Accept|Cache-Control|Host| User-Agent|event_type|           timestamp|
|------|-------------|----|-----------|----------|--------------------|
|   */*|     no-cache| moe|curl/7.47.0|join_guild|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|join_guild|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|join_guild|2018-07-29 18:31:...|
|   */*|     no-cache| moe|curl/7.47.0|join_guild|2018-07-29 18:31:...|



## Having seen our published events and how they can be stored and filtered from our Hadoop file system, we'll revise our API to handle and filter different events and schema.

```
docker-compose exec mids \
  env FLASK_APP=/w205/assignment-12-colbycarter/game_api.py \
  flask run --host 0.0.0.0
```

## We use Apache Bench to call our API from different hosts to generate different schema.

```
docker-compose exec mids \
  ab \
    -n 10 \
    -H "Host: user1.comcast.com" \
    http://localhost:5000/
    
docker-compose exec mids \
  ab \
    -n 10 \
    -H "Host: user1.comcast.com" \
    http://localhost:5000/purchase_a_sword

docker-compose exec mids \
  ab \
    -n 10 \
    -H "Host: user2.att.com" \
    http://localhost:5000/

docker-compose exec mids \
  ab \
    -n 10 \
    -H "Host: user2.att.com" \
    http://localhost:5000/purchase_a_sword
```

## This breaks our previous `separate_events.py` program, so we use the following to handle different purchase schemas, which we'll test with a second type of purchase.

```
#!/usr/bin/env python
"""Extract events from kafka and write them to hdfs
"""
import json
from pyspark.sql import SparkSession, Row
from pyspark.sql.functions import udf


@udf('boolean')
def is_purchase(event_as_json):
    event = json.loads(event_as_json)
    if event['event_type'] == 'purchase_sword':
        return True
    return False


def main():
    """main
    """
    spark = SparkSession \
        .builder \
        .appName("ExtractEventsJob") \
        .getOrCreate()

    raw_events = spark \
        .read \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", "events") \
        .option("startingOffsets", "earliest") \
        .option("endingOffsets", "latest") \
        .load()

    purchase_events = raw_events \
        .select(raw_events.value.cast('string').alias('raw'),
                raw_events.timestamp.cast('string')) \
        .filter(is_purchase('raw'))

    extracted_purchase_events = purchase_events \
        .rdd \
        .map(lambda r: Row(timestamp=r.timestamp, **json.loads(r.raw))) \
        .toDF()
    extracted_purchase_events.printSchema()
    extracted_purchase_events.show()


if __name__ == "__main__":
    main()
```

## So we exec using spark-submit again, this time handling for when the event is a purchase to trigger our filter.

```
docker-compose exec spark \
  spark-submit /w205/assignment-12-colbycarter/just_filtering.py
```

## This now produced a structured query of just our purchase results with different hosts.


|Accept|             Host|     User-Agent|    event_type|           timestamp|
|------|-----------------|---------------|--------------|--------------------|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|user1.comcast.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:04:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|
|   */*|    user2.att.com|ApacheBench/2.3|purchase_sword|2018-08-05 23:05:...|


## Next we add another type of purchase to our events, which has different metadata.

```
@app.route("/purchase_a_knife")
def purchase_a_knife():
    purchase_knife_event = {'event_type': 'purchase_knife',
                            'description': 'very sharp knife'}
    log_to_kafka('events', purchase_knife_event)
    return "Knife Purchased!\n"
```

## Correspondingly, we adjust our `is_purchase` events filter to include "purchase_knife" and re-launch our API.

```
@udf('boolean')
def is_purchase(event_as_json):
    event = json.loads(event_as_json)
    if event['event_type'] in ('purchase_sword','purchase_knife'):
        return True
    return False
```
 
## We exec with Apache Bench again from the two users, now handling the schema of the additional metadata.

```
docker-compose exec mids \
  ab \
    -n 10 \
    -H "Host: user1.comcast.com" \
    http://localhost:5000/purchase_a_knife

docker-compose exec mids \
  ab \
    -n 10 \
    -H "Host: user2.att.com" \
    http://localhost:5000/purchase_a_knife
```

## We use the modified `filtered_writes.py` which handles the schema for a "purchase_knife" event and then writes to parquet files.

```
docker-compose exec spark \
    spark-submit /w205/assignment-12-colbycarter/filtered_writes.py
```


|Accept|             Host|     User-Agent|     description|    event_type|           timestamp|
|------|-----------------|---------------|----------------|--------------|--------------------|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|    user2.att.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|


## We then check our HDFS to confirm the files are there.

```
docker-compose exec cloudera hadoop fs -ls /tmp/
docker-compose exec cloudera hadoop fs -ls /tmp/purchases/
```

Resulting parque file:

```
/tmp/purchases/part-00000-74eb79e7-b7bf-4f00-99fe-7d8688c1debb-c000.snappy.parquet
```

## We can then pull these files into a Jupyter notebook by executing Spark.

```
docker-compose exec spark \
  env \
    PYSPARK_DRIVER_PYTHON=jupyter \
    PYSPARK_DRIVER_PYTHON_OPTS='notebook --no-browser --port 8888 --ip 0.0.0.0 --allow-root' \
  pyspark
```

## We need to create a symbolic link to our w205 folder from our current directory.

```
docker-compose exec spark bash
ln -s  /w205 w205
```

## In our notebook, we read in the parquet and show the data, which creates the same table from above.

```
purchases = spark.read.parquet('/tmp/purchases')
purchases.show()
```

## Next, we store it as a temporary table and then query it to our Comcast user only.

```
purchases.registerTempTable('purchases')
purchases_by_example2 = spark.sql("select * from purchases where Host = 'user1.comcast.com'")
purchases_by_example2.show()
```

As expected, we get:


|Accept|             Host|     User-Agent|     description|    event_type|           timestamp|
|------|-----------------|---------------|----------------|--------------|--------------------|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|
|   */*|user1.comcast.com|ApacheBench/2.3|very sharp knife|purchase_knife|2018-08-06 02:52:...|


## Lastly, we show that we can read this temporary table into a Panda dataframe.

```
df = purchases_by_example2.toPandas()
df.describe()
```


## To end this exercise, we save our notebook, exit our spark and kafka containers, and then tear our remaining containers down.

```
docker-compose down
docker ps -a
```

