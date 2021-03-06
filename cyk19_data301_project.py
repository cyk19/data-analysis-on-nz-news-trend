# -*- coding: utf-8 -*-
"""cyk19_DATA301_project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1NUnO3eR4KMll_sUbvacTI2yUQRut8z9x
"""

#library and code setup
!apt-get install openjdk-8-jdk-headless -qq > /dev/null
!pip install -q pyspark
!pip install gdelt

import pyspark, os
from pyspark import SparkConf, SparkContext
os.environ["PYSPARK_PYTHON"]="python3"
os.environ["JAVA_HOME"]="/usr/lib/jvm/java-8-openjdk-amd64/"

#start spark local server
import sys, os
from operator import add
import time

os.environ["PYSPARK_PYTHON"]="python3"

import pyspark
from pyspark import SparkConf, SparkContext

#connects our python driver to a local Spark JVM running on the Google Colab server virtual machine
try:
  conf = SparkConf().setMaster("local[*]").set("spark.executor.memory", "1g")
  sc = SparkContext(conf = conf)
except ValueError:
  #it's ok if the server is already started
  pass

def dbg(x):
  """ A helper function to print debugging information on RDDs """
  if isinstance(x, pyspark.RDD):
    print([(t[0], list(t[1]) if 
            isinstance(t[1], pyspark.resultiterable.ResultIterable) else t[1])
           if isinstance(t, tuple) else t
           for t in x.take(100)])
  else:
    print(x)

from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
import pandas as pd
import gdelt
import os

# set up gdeltpyr for version 2
gd = gdelt.gdelt(version=2)

# multiprocess the query
e = ProcessPoolExecutor()


# generic functions to pull and write data to disk based on date
def get_filename(x):
  date = x.strftime('%Y%m%d')
  return "{}_gdeltdata.csv".format(date)

def intofile(filename, error_dates):
    try:
        if not os.path.exists(filename):
          date = filename.split("_")[0]
          d = gd.Search(date, table='events',coverage=False) #not updata at 15mins
          d.to_csv(filename,encoding='utf-8',index=False)
    except:
        error_dates.append(filename)
        print("Error occurred")

# pull the data from gdelt into multi files; this may take a long time
dates = [get_filename(x) for x in pd.date_range('2020 January 1','2020 April 30')]

error_dates = []

# Extract dates which does not have a url
for date in dates:
  intofile(date, error_dates)
  
dates = list(set(dates) - set(error_dates))

from pyspark.sql import SQLContext
sqlContext = SQLContext(sc)

data = sqlContext.read.option("header", "true").csv(dates)

# A-priori and market-basket analysis
time_start = time.time()


def getEventActorCategoryPair(event, freq_actors):
  pairs = []
  if event["Actor1Code"] != None and event["Actor1Code"] in freq_actors:
    pairs.append(((event["Actor1Code"], event["EventRootCode"]), 1))
  if event["Actor2Code"] != None and event["Actor2Code"] in freq_actors:
    pairs.append(((event["Actor2Code"], event["EventRootCode"]), 1))
  return pairs

def getEventActor(event):
  actors = []
  if event["Actor1Code"] != None:
    actors.append((event["Actor1Code"], 1))
  if event["Actor2Code"] != None:
    actors.append((event["Actor2Code"], 1))
  return actors

def computeConfidence(supportActorEventCodeActor):
  supportActorEventCode = supportActorEventCodeActor[1][0][1]
  supportActor = supportActorEventCodeActor[1][1]
  confidenceActorEventCode = supportActorEventCode / supportActor
  return ((supportActorEventCodeActor[0], supportActorEventCodeActor[1][0][0]), confidenceActorEventCode)
  
def computeInterest(confActorEventCodesupportEventCode, num_events):
  supportEventCode = confActorEventCodesupportEventCode[1][1]
  probEventCode = supportEventCode/num_events
  confActorEventCode = confActorEventCodesupportEventCode[1][0][1]
  interestActorEventCode = confActorEventCode - probEventCode
  return ((confActorEventCodesupportEventCode[1][0][0], confActorEventCodesupportEventCode[0]), interestActorEventCode)



months = ["202001", "202002", "202003", "202004"]
month_interest_dict = {}

for month in months:
  freqThres = 10

  # extra check to only extract event which happened in that month
  data_subset = data.rdd.filter(lambda x: x["ActionGeo_CountryCode"] == "NZ").filter(lambda x: x["MonthYear"] == month)
  num_events = len(data_subset.collect())
  data_subset_actor = data_subset.flatMap(lambda x: getEventActor(x))
  data_subset_actor_freq = data_subset_actor.reduceByKey(lambda a,b: a+b).filter(lambda x: x[1] >= freqThres)
  freq_actors = data_subset_actor_freq.map(lambda x: x[0]).collect()
  freq_actors_bc = sc.broadcast(freq_actors)


  data_subset_pairs = data_subset.flatMap(lambda x: getEventActorCategoryPair(x, freq_actors_bc.value))
  data_subset_pairs_freq = data_subset_pairs.reduceByKey(lambda a,b: a+b).filter(lambda x: x[1] >= freqThres)

  supportActorEventCode = data_subset_pairs_freq.map(lambda x: (x[0][0], (x[0][1], x[1])))
  supportActorEventCodeActor = supportActorEventCode.join(data_subset_actor_freq)
  confidenceActorEventCode = supportActorEventCodeActor.map(lambda x: computeConfidence(x))
  dbg(confidenceActorEventCode)


  supportEventCode = data_subset.map(lambda x: (x["EventRootCode"], 1)).reduceByKey(lambda a,b: a+b)
  confActorEventCode = confidenceActorEventCode.map(lambda x: (x[0][1], (x[0][0], x[1])))
  confActorEventCodesupportEventCode = confActorEventCode.join(supportEventCode)
  interestActorEventCode = confActorEventCodesupportEventCode.map(lambda x: computeInterest(x, num_events))
  month_interest_dict[month] = interestActorEventCode.sortBy(lambda x: -1*x[1]).collect()

print(month_interest_dict)

# Cosine similarity

import math

month_interestVector_dict = {}

# Compute interest vectors for each month using the top5 pairs in January 2020 as reference
for year in month_interest_dict.keys():
  interestVector = []
  for pair_ref, interest_ref in month_interest_dict["202001"]:
    isFound = False
    for pair, interest in month_interest_dict[year]:
      if pair == pair_ref:
        isFound = True
        interestVector.append(interest)
    if not isFound:
      interestVector.append(0)
  month_interestVector_dict[year] = interestVector


interestVector_2019 = sc.parallelize(month_interest_dict["202001"]).map(lambda x: x[1]).collect()
month_interestVector_dict["202001"] = interestVector_2019


def cosine_similarity(ref_vector, vector):
  numerator = 0
  squared_ref_vector = 0
  squared_vector = 0
  for i in range(len(ref_vector)):
    numerator += ref_vector[i] * vector[i]
    squared_ref_vector += ref_vector[i] * ref_vector[i]
    squared_vector += vector[i] * vector[i]
  root_ref_vector = math.sqrt(squared_ref_vector)
  root_vector = math.sqrt(squared_vector)
  denominator = root_ref_vector * root_vector
  if denominator == 0:
    return 0
  return numerator/denominator


year_similarity_dict = {}
for year in month_interestVector_dict.keys():
  year_similarity_dict[year] = cosine_similarity(month_interestVector_dict["202001"], month_interestVector_dict[year])

print(year_similarity_dict)

time_end = time.time()
print("elapsed time is %s" % str(time_end-time_start))