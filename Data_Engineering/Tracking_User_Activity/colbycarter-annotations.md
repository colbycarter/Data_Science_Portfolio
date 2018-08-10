# Colby's annotations, Assignment 8

Summary: in this exercise, we use kafka and spark containers to consume messages from our created topic, and view our JSON assessments data as a pyspark dataframe with the JSON objects represented as strings for ease of reading. 

## Here we open the assignment directory in our mids205 container and copy the docker-compose file edited in class.

```
docker run -it --rm -v /home/science/w205:/w205 midsw205/base:latest bash
cd assignment-08-colbycarter/
cp ~/w205/course-content/08-Querying-Data/docker-compose.yml .
cp ~/w205/assignment-07-colbycarter/colbycarter-annotations.md .
```

## Here we get the data from Github and exit the container.

```
curl -L -o assessment-attempts-20180128-121051-nested.json https://goo.gl/f5bRm4
exit
```

## Next, we spin up the kafka, zookeeper, and mids clusters and log events in a second droplet window.

```
cd ~/w205/assignment-08-colbycarter/
docker-compose up -d
docker ps -a
docker-compose logs -f kafka
```

## We'll also create a temporary location for our Hadoop file system.

```
docker-compose exec cloudera hadoop fs -ls /tmp/
```

## Next we create a new topic using the same zookeeper port as our yml, sticking with the name "tests", check that it worked and look at the data.

```
docker-compose exec kafka kafka-topics --create --topic tests --partitions 1 --replication-factor 1 --if-not-exists --zookeeper zookeeper:32181
```

This confirms our topic, as does the following kafka exec which shows the single topic:
```
Created topic "tests".
```

```
docker-compose exec kafka kafka-topics --describe --topic tests --zookeeper zookeeper:32181
```

## Execute bash from the mids container, piping the json objects to the kafkacat utility and publish as messages to "tests".

```
docker-compose exec mids bash -c "cat /w205/assignment-08-colbycarter/assessment-attempts-20180128-121051-nested.json | jq '.[]' -c | kafkacat -P -b kafka:29092 -t tests"
```


## Subscribe to the first ten messages from "tests" using the kafka utility.

```
docker-compose exec kafka kafka-console-consumer --bootstrap-server kafka:29092 --topic tests --from-beginning --max-messages 10
```

## Count the number of messages by piping each line. There are 3,281 messages.

```
docker-compose exec mids bash -c "kafkacat -C -b kafka:29092 -t tests -o beginning -e" | wc -l
```

## Now we're going to exec into our pyspark container.

```
docker-compose exec spark pyspark
```

## Using python, we create a spark object for subscribing to our messages from the json data.

```
raw_tests = spark.read.format("kafka").option("kafka.bootstrap.servers", "kafka:29092").option("subscribe","tests").option("startingOffsets", "earliest").option("endingOffsets", "latest").load() 
```

## We'll use the object's print method to look at the schema and cache.

```
raw_tests.printSchema()
raw_tests.show()
```


| key|               value| topic|partition|offset|           timestamp|timestampType|
|----|--------------------|------|---------|------|--------------------|-------------|
|null|[7B 22 6B 65 65 6...| tests|        0|     0|1969-12-31 23:59:...|            0|
|null|[7B 22 6B 65 65 6...| tests|        0|     1|1969-12-31 23:59:...|            0|
|null|[7B 22 6B 65 65 6...| tests|        0|     2|1969-12-31 23:59:...|            0|
|null|[7B 22 6B 65 65 6...| tests|        0|     3|1969-12-31 23:59:...|            0|
|null|[7B 22 6B 65 65 6...| tests|        0|     4|1969-12-31 23:59:...|            0|


```
raw_tests.cache()
```

Cache:
```
DataFrame[key: binary, value: binary, topic: string, partition: int, offset: bigint, timestamp: timestamp, timestampType: int]
```

## Because we can't read the value field from binary, we use the spark object's select method to cast it as a string.

```
tests_as_strings=raw_tests.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")
test_as_strings.show()
```


| key|               value|
|----|--------------------|
|null|{"keen_timestamp"...|
|null|{"keen_timestamp"...|
|null|{"keen_timestamp"...|


## Using spark, we see that there are actually 3,280 messages.

```
tests_as_strings.count()
```

## We can select the from the value field at row 1 to see an example of the nested json object.

```
tests__as_strings.select('value').take(1)
```

A truncated look at the first object:

```
[Row(value='{"keen_timestamp":"1516717442.735266","max_attempts":"1.0"...
```

## Or we can be more precise and take the unrolled view of the first example, just showing the value with out the [Row...] wrapping.

```
tests_as_strings.select('value').take(1)[0].value
```

## We also want to observe an example json object from the spark dataframe using the loads function from the json package, which prints the same first value of 1.

```
import json
first_message=json.loads(tests_as_strings.select('value').take(1)[0].value)
first_message
```

## This produces a cleaner json object in Python that looks more like a dictionary of the first message.

```
{'keen_timestamp': '1516717442.735266', 'max_attempts': '1.0', 'started_at': '2018-01-23T14:23:19.082Z',...
```

## Because the message is like a python dictionary, we can index to different parts of the message, such as the question and whether the user was correct.

```
print(first_message['sequences']['questions'][1])
```

## For our example assessment-taker this produces, the following plus additional nested information.

```
{'user_incomplete': False, 'user_correct': False, 'options': [{'checked': True, 'at': '2018-01-23T14:23:30.116Z',...
```

## More interestingly, we can get counts of number of submitted, correct, incorrect, etc. answers.

```
print(first_message['sequences']['counts'])
```

## For our examples, there were 2 correct answers, one incorrect, and one incomplete.

```
{'incomplete': 1, 'submitted': 4, 'incorrect': 1, 'all_correct': False, 'correct': 2, 'total': 4, 'unanswered': 0}
```



# [ADD HADOOP STEPS HERE]

## We'll now write our string-cast messages object to our Hadoop temporary file system as parquet files.

```
tests = raw_tests.select(raw_tests.value.cast('string'))
tests.write.parquet("/tmp/tests")
```

## We then extract values from our parquet files using a lambda function to put them into a structured dataframe.

```
import json
extracted_tests = tests.rdd.map(lambda x: json.loads(x.value)).toDF()
```

## Viewing the dataframe and schema, we see structured fields like time stamps, user ids, and the name of the exam taken.

```
extracted_tests.show()
```

```
 extracted_tests.printSchema()
```

```
root
 |-- base_exam_id: string (nullable = true)
 |-- certification: string (nullable = true)
 |-- exam_name: string (nullable = true)
 |-- keen_created_at: string (nullable = true)
 |-- keen_id: string (nullable = true)
 |-- keen_timestamp: string (nullable = true)
 |-- max_attempts: string (nullable = true)
 |-- sequences: map (nullable = true)
 |    |-- key: string
 |    |-- value: array (valueContainsNull = true)
 |    |    |-- element: map (containsNull = true)
 |    |    |    |-- key: string
 |    |    |    |-- value: boolean (valueContainsNull = true)
 |-- started_at: string (nullable = true)
 |-- user_exam_id: string (nullable = true)
```

## Knowing the schema of the dataframe, we can register it as a temporary table to be queried with Spark SQL. Here we get whether the user was correct on a given question.

```
extracted_tests.registerTempTable('tests')
spark.sql("select user_exam_id, exam_name, max_attempts, sequences.questions[0].user_correct from tests limit 10").show()
```


|        user_exam_id|           exam_name|max_attempts|sequences[questions] AS `questions`[0][user_correct]|
|--------------------|--------------------|------------|----------------------------------------------------|
|6d4089e4-bde5-4a2...|Normal Forms and ...|         1.0|                                               false|
|2fec1534-b41f-441...|Normal Forms and ...|         1.0|                                                true|
|8edbc8a8-4d26-429...|The Principles of...|         1.0|                                               false|
|c0ee680e-8892-4e6...|The Principles of...|         1.0|                                                true|
|e4525b79-7904-405...|Introduction to B...|         1.0|                                               false|
|3186dafa-7acf-47e...|        Learning Git|         1.0|                                                true|
|48d88326-36a3-4cb...|Git Fundamentals ...|         1.0|                                                true|
|bb152d6b-cada-41e...|Introduction to P...|         1.0|                                                true|
|70073d6f-ced5-4d0...|Intermediate Pyth...|         1.0|                                                true|
|9eb6d4d6-fd1f-4f3...|Introduction to P...|         1.0|                                               false|


## We can store this query output in an object and write it to a temporary parque file.

```
test_info = spark.sql("select user_exam_id, exam_name, max_attempts, sequences.questions[0].user_correct as correct from tests limit 10")
test_info.write.parquet("/tmp/test_info")
```

## We then look at our temp Hadoop distributed file system.

```
docker-compose exec cloudera hadoop fs -ls /tmp/
docker-compose exec cloudera hadoop fs -ls /tmp/tests/
```

## This shows we successfully created our parquet file with ten rows of data.
```
Found 2 items
-rw-r--r--   1 root supergroup          0 2018-07-08 16:23 /tmp/tests/_SUCCESS
-rw-r--r--   1 root supergroup    2513397 2018-07-08 16:23 /tmp/tests/part-00000-17ba0d91-e396-4297-ab8a-5adc389c713f-c000.snappy.parquet
```



## Having viewed the top of our data and stored our data, we exit spark with 

`exit()`

## And then tear down the cluster and verify.

```
docker-compose down
docker ps -a
```

