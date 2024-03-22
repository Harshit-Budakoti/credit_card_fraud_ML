# -*- coding: utf-8 -*-
"""Untitled6.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1zD8rilWmjz0w3b7EmU2UohINKIyViUkE
"""
from dagshub.streaming import install_hooks
install_hooks()

import os

dataset1_path = os.getenv('DATASET1_PATH')
dataset2_path = os.getenv('DATASET2_PATH')

from pyspark.sql import SparkSession

# Initialize a SparkSession
spark = SparkSession.builder.getOrCreate() 
file_path1 = dataset1_path #s3://credit_card_fraud_ML/old_raw_dataframe.parquet
file_path2 = dataset2_path #s3://credit_card_fraud_ML/new_raw_dataframe.parquet

# Read the CSV file
df = spark.read.parquet(file_path, inferSchema=True, header=True)
import pyspark
from pyspark.sql.functions import col, regexp_replace, substring

def str_truncate(df, column, delimiter):
    df = df.withColumn(column, regexp_replace(df[column], delimiter, ''))
    return df

def split_to_feature(df, column, new_feature, start_index, stop_index):
    df = df.withColumn(new_feature, substring(col(column), start_index, stop_index))
    return df

def year_month(df, column):
    df = df.withColumn(column+'_num', (col(column)/100).cast('integer'))
    return df

def to_int(df, column):
    df = df.withColumn(column, col(column).cast('integer'))
    return df

def age_cal(df, dob_col, trans_date_col):
    df = df.withColumn('age_at_time_of_transaction', ((col(trans_date_col) - col(dob_col)).cast('integer')/100).cast('integer'))
    return df

def drop_cols(df, columns):
    if isinstance(columns, str):
        df = df.drop(columns)
    elif isinstance(columns, list):
        df = df.drop(*columns)
    else:
        print("INVALID ARGUMENTS")
    return df
df1 = spark.read.csv(dataset1_path, header=True, inferSchema=True)
df2 = spark.read.csv(dataset2_path, header=True, inferSchema=True)
def all_preprocess_commands(df):
    df = str_truncate(df, 'ssn', '-')
    df = str_truncate(df, 'dob', '-')
    df = str_truncate(df, 'trans_date', '-')
    df = to_int(df, 'dob')
    df = to_int(df, 'trans_date')
    df = year_month(df, 'dob')
    df = year_month(df, 'trans_date')
    df = age_cal(df, 'dob_num', 'trans_date_num')
    df = drop_cols(df, ['dob_num', 'trans_date_num'])
    df = str_truncate(df, 'trans_time', ':')
    df = str_truncate(df, 'trans_time', '2024-02-28')
    df = str_truncate(df, 'trans_time', ' ')
    df = to_int(df, 'trans_time')
    df = split_to_feature(df, 'ssn', 'area_code_ssn', 1, 3)
    df = split_to_feature(df, 'dob', 'mm-dd', 5, 8)
    df = drop_cols(df, ['mm-dd', 'street', 'city', 'state', 'first', 'last'])
    df = drop_cols(df, ['dob', 'trans_time'])
    df = to_int(df, 'ssn')
    df = to_int(df, 'area_code_ssn')
    df = drop_cols(df, ['area_code_ssn', 'cc_num', 'trans_num'])
    def week_month_and_hour(dfr):
        from pyspark.sql.functions import unix_timestamp, from_unixtime, dayofweek, hour,month
        dfr = dfr.withColumn("timestamp_str", from_unixtime(dfr.unix_time, "yyyy-MM-dd HH:mm:ss"))
        #(1 = Sunday, 2 = Monday, ..., 7 = Saturday)
        dfr = dfr.withColumn("day", dayofweek(dfr.timestamp_str))
        dfr = dfr.withColumn("hour", hour(dfr.timestamp_str))
        dfr = dfr.withColumn("month", month(dfr.timestamp_str))
        return dfr
    df = week_month_and_hour(df)
    return df
df1 = all_preprocess_commands(df1)
df2 = all_preprocess_commands(df2)
df1.write.mode('overwrite').parquet('processed_old_data.parquet')
df2.write.mode('overwrite').parquet('processed_new_data.parquet')

from dagshub import get_repo_bucket_client
s3 = get_repo_bucket_client("harshitbudakotimatsc20/credit_card_fraud_ML")

# Upload file
s3.upload_file(
    Bucket="credit_card_fraud_ML",  # name of the repo
    Filename="processed_old_data.parquet",  # local path of file to upload
    Key="processed_old_data.parquet"  # remote path where to upload the file
)
s3.upload_file(
    Bucket="credit_card_fraud_ML",  # name of the repo
    Filename="processed_new_data.parquet",  # local path of file to upload
    Key="processed_new_data.parquet"  # remote path where to upload the file
)
# stop the SparkSession
spark.stop()

