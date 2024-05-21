from flask import Flask, jsonify, send_file
from pymongo import MongoClient
import pandas as pd
import random
import requests
import jwt
import pymongo
import os
import time
from datetime import datetime, timedelta

MONGO_URI = os.environ.get('MONGO_URL')

if MONGO_URI:
    print("MongoDB URL:", MONGO_URI)
else:
    print("MONGO_URL environment variable not set.")

client = pymongo.MongoClient(MONGO_URI)

print("Connection Suuccessfull")

# MongoDB's connection details
# MONGO_URI = "mongodb+srv://kaushikjasoliya6:MGEwjGpGQ7oG5ed6@medicineprediction.pd4mqou.mongodb.net/"
DATABASE_NAME = "healthray_prediction"
COLLECTION_DATA_TABLE = "New_AI_data_base"
COLLECTION_DATA_TABLE_MAPPING = "New_AI_data_base_MIX"
COLLECTION_ID_TABLE = "New_AI_Date_table"

# JWT secret key
# JWT_SECRET_KEY = 'KcXLnP62HH9.NuP{J-z*nu&KV&wUq-+m'
# API_URL = "http://203.112.156.220:4000/api/v1"
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
API_URL = os.environ.get('API_URL')

if JWT_SECRET_KEY and API_URL:
    print("JWT_SECRET_KEY :", JWT_SECRET_KEY)
    print("API_URL :", API_URL)
else:
    print("API_URL and JWT_SECRET_KEY environment variable not set.")

# Generate JWT token
JWT_TOKEN = jwt.encode({"data": {"platform": "Python"}}, JWT_SECRET_KEY, 'HS256')
HEADER = {'Authorization': f'{JWT_TOKEN}'}

START_DATE_OBJECT = "2023-03-01"
DATE_FORMATE = "%Y-%m-%d"
START_DATE = datetime.strptime(START_DATE_OBJECT, DATE_FORMATE).date()

# Get the current date
CURRENT_DATE = datetime.now()

# Convert CURRENT_DATE to datetime.datetime object
CURRENT_DATE = datetime.combine(CURRENT_DATE, datetime.min.time())

# Get the previous date
PREVIOUS_DATE = CURRENT_DATE - timedelta(days=1)

#Interval for adding data in database
INTERVAL = timedelta(days=90)

# Methos for add doc_id and sync date
def add_doc_id_to_mongodb(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE,doctor_id,date):
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_ID_TABLE]

    if doctor_id:
        
        # Add new entry if document does not exist
        data = {
            "Doctor_ID": doctor_id,
            "Last_Sync_Date": date
        }
        collection.insert_one(data)
        print(f"Added new entry for Doctor_ID {doctor_id} and Sync Date {date}")

# Method for update sync date
def update_last_sync_date_to_mongodb(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE,doctor_id,date):
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_ID_TABLE]
    
    if doctor_id:
        # Check if document already exists for Doctor_ID
        document = collection.find_one({"Doctor_ID": doctor_id})

        if document:
            # Update Last_Sync_Date if document exists
            collection.update_one({"Doctor_ID": doctor_id}, {"$set": {"Last_Sync_Date": date}})
        else:
            print(f"Entry not found for {doctor_id}")
    return date
        
# Method for check last sync date
def check_last_sync_date(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE,Doctor_ID):
    
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_ID_TABLE]

    # Query MongoDB for the last_sync_date of the specified doc_id
    document = collection.find_one({"Doctor_ID": Doctor_ID})

    # Check if the document exists
    if document:
        # Check if Last_Sync_Date exists in the document
        if "Last_Sync_Date" in document:
            last_sync_date = document["Last_Sync_Date"]
            if last_sync_date:
                return last_sync_date
            else:
                return None
        else:
            print(f"Last sync date for Doctor_ID {Doctor_ID} not found in document.")
            return None
    else:
        print(f"Document for Doctor_ID {Doctor_ID} not found.")
        return None

# call api (With date range) and insert dta in mongoDB
def insert_data_to_mongodb(API_URL, HEADER, MONGO_URI, DATABASE_NAME, COLLECTION_DATA_TABLE, COLLECTION_DATA_TABLE_MAPPING, doctor_id, start_date, end_date):

    if doctor_id:
        
        print(f"start_date :- {start_date} // End date :- {end_date}")

        response = requests.get(
            f"{API_URL}/doctor/topic_list/{doctor_id}?start_date={start_date}&end_date={end_date}",
            headers=HEADER)

        if response.status_code == 200:
            api_data = response.json()
            data = api_data['data']['data']
            doctor_name = api_data['data'].get('doctor_name', None)

            client = pymongo.MongoClient(MONGO_URI)
            db = client[DATABASE_NAME]
            collection = db[COLLECTION_DATA_TABLE]
            collection2 = db[COLLECTION_DATA_TABLE_MAPPING]    
            
            mongo_data = []
            mongo_data2 = []
        # For Prediction
            for item in data:
                
                doctor_data = {
                    "doctor_id": doctor_id
                }
                symptom_ids = [symptom['dynamic_topic_id'] for symptom in item['Complains/Symptoms']]
                symptom_names = [symptom['name'] for symptom in item['Complains/Symptoms']]
                prescriptions = item['Prescription/Rx']

                formatted_diagnoses = ", ".join(
                    [f"{diagnosis['name']} ({diagnosis['dynamic_topic_id']})" for diagnosis in item['Diagnosis']])
                formatted_advice = ", ".join(
                    [f"{advice['name']} ({advice['dynamic_topic_id']})" for advice in
                     item.get('General Advice', [])])
                formatted_prescriptions = ""
                if prescriptions:
                    formatted_prescriptions = ", ".join(
                        [f"{prescription['medicine_name']} ({prescription['standard_medicine_id']})" for
                         prescription in prescriptions])

                for symptom_id, symptom_name in zip(symptom_ids, symptom_names):
                    document = {
                        "Doctor_ID": doctor_id,
                        "Symptom_ID": symptom_id,
                        # "Symptom": symptom_names,
                        "Prescriptions": formatted_prescriptions if formatted_prescriptions else "None",
                        "Diagnosis": formatted_diagnoses if formatted_diagnoses else "None",
                        "Advice": formatted_advice if formatted_advice else "None"
                    }
                    mongo_data.append(document)
 
        # For Mapping    
            for item in data:
                
                doctor_data = {
                    "doctor_id": doctor_id
                }
                # symptom_ids = [symptom['dynamic_topic_id'] for symptom in item['Complains/Symptoms']]
                # symptom_names = [symptom['name'] for symptom in item['Complains/Symptoms']]
                prescriptions = item['Prescription/Rx']

                formatted_symptom_id = ", ".join(
                    [f"{symptom['dynamic_topic_id']}" for symptom in item['Complains/Symptoms']])
                formatted_diagnoses = ", ".join(
                    [f"{diagnosis['name']} ({diagnosis['dynamic_topic_id']})" for diagnosis in item['Diagnosis']])
                formatted_advice = ", ".join(
                    [f"{advice['name']} ({advice['dynamic_topic_id']})" for advice in
                     item.get('General Advice', [])])
                formatted_prescriptions = ""
                if prescriptions:
                    formatted_prescriptions = ", ".join(
                        [f"{prescription['medicine_name']} ({prescription['standard_medicine_id']})" for
                         prescription in prescriptions])

                document = {
                    "Doctor_ID": doctor_id,
                    "Symptom_ID": formatted_symptom_id,
                    # "Symptom": symptom_names,
                    "Prescriptions": formatted_prescriptions if formatted_prescriptions else "None",
                    "Diagnosis": formatted_diagnoses if formatted_diagnoses else "None",
                    "Advice": formatted_advice if formatted_advice else "None"
                }
                mongo_data2.append(document)

            df = pd.DataFrame(mongo_data)
            df2 = pd.DataFrame(mongo_data2)

            if df2.empty:
                print(f"No data available for doctor ID {doctor_id}")
            else:
                fill_missing_text_data(df, "Advice")
                fill_missing_text_data(df, "Prescriptions")
                fill_missing_text_data(df, "Diagnosis")

                data_dict = df.to_dict(orient='records')
                collection.insert_many(data_dict)
                
                data_dict2 = df2.to_dict(orient='records')
                collection2.insert_many(data_dict2)

                print(f"Data Added in MongoDB form {start_date} to {end_date} for ID {doctor_id}..")
        else:
            print(f"Error: {response.status_code} - {response.text}")

# Method for Add data in database in date wise
def sync_data_to_mongodb(API_URL, HEADER, MONGO_URI, DATABASE_NAME, COLLECTION_DATA_TABLE,COLLECTION_DATA_TABLE_MAPPING, COLLECTION_ID_TABLE, doc_id, sync_date, INTERVAL,CURRENT_DATE):

    end_date = sync_date
    ending_date = datetime.combine(end_date, datetime.min.time())
    date = sync_date
    while ending_date < CURRENT_DATE:
        starting_date = ending_date + timedelta(days=1)
        ending_date += INTERVAL
        print(f"start_date {starting_date} - end_date {ending_date}")

        insert_data_to_mongodb(API_URL, HEADER, MONGO_URI, DATABASE_NAME, COLLECTION_DATA_TABLE,COLLECTION_DATA_TABLE_MAPPING, doc_id, starting_date, ending_date)
        
        print(f"INSERTION PROCESS DONE FOR {doc_id} AND DATE IS {sync_date} TO {ending_date}")

        if ending_date > CURRENT_DATE:
            date = update_last_sync_date_to_mongodb(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE, doc_id, CURRENT_DATE)
        else:
            date = update_last_sync_date_to_mongodb(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE, doc_id, ending_date)

    print(f"LAST SYNC DATE IS {date} UPDATED FOR {doc_id}")

#Fill data in mongoDB Database
class FillDataInDataBase:
    def __init__(self):
        # Connection To MongoDB
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection_data = db[COLLECTION_DATA_TABLE]
        collection_id = db[COLLECTION_ID_TABLE]

        response_doctor_list = requests.get(API_URL + "/doctor/get_ai_doctors", headers=HEADER)
        
        data = response_doctor_list.json()
        doctor_id_list = data['data']
        

        print(f"Main Doctor ID list {doctor_id_list}")
        
        # Count the number of documents in the collection
        count = collection_id.count_documents({})
        
        if count > 0:
            for doc_id in doctor_id_list:
                
                # Check if document already exists for Doctor_ID
                document = collection_id.find_one({"Doctor_ID": doc_id})
                
                if document:

                    sync_date = check_last_sync_date(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE,doc_id)
                    
                    if sync_date:
                        
                        sync_data_to_mongodb(API_URL, HEADER, MONGO_URI, DATABASE_NAME, COLLECTION_DATA_TABLE,COLLECTION_DATA_TABLE_MAPPING, COLLECTION_ID_TABLE, doc_id, sync_date, INTERVAL,CURRENT_DATE)

                else:
                    DATE = datetime.combine(START_DATE, datetime.min.time())
                    add_doc_id_to_mongodb(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE,doc_id,DATE)

                    sync_date = check_last_sync_date(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE,doc_id)

                    if sync_date:
                        
                        sync_data_to_mongodb(API_URL, HEADER, MONGO_URI, DATABASE_NAME, COLLECTION_DATA_TABLE,COLLECTION_DATA_TABLE_MAPPING, COLLECTION_ID_TABLE, doc_id, sync_date, INTERVAL,CURRENT_DATE)
 

        else:
            for doc_id in doctor_id_list:

                DATE = datetime.combine(START_DATE, datetime.min.time())
                add_doc_id_to_mongodb(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE,doc_id,DATE)

                sync_date = check_last_sync_date(MONGO_URI, DATABASE_NAME, COLLECTION_ID_TABLE,doc_id)

                if sync_date:
                    
                    sync_data_to_mongodb(API_URL, HEADER, MONGO_URI, DATABASE_NAME, COLLECTION_DATA_TABLE,COLLECTION_DATA_TABLE_MAPPING, COLLECTION_ID_TABLE, doc_id, sync_date, INTERVAL,CURRENT_DATE)                               
                    
# Insert data into MongoDB
def fill_missing_text_data(dataframe, column_name):
    # Identify available text values in the specified column
    available_values = set(dataframe[column_name].dropna())
    # Fill missing values in the specified column with a randomly selected available text value
    missing_indices = dataframe[dataframe[column_name] == "None"].index
    # print(missing_indices)
    for index in missing_indices:
        if available_values:
            fill_value = random.choice(list(available_values))
            dataframe.at[index, column_name] = fill_value

# Create Object Fill Data In MongoDB Data Base
FILL_DATA_IN_DATABASE = FillDataInDataBase()





