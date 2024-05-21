import pickle
import csv
import pymongo
import pandas as pd
import os
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

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

CSV_FILE = "./Doctor_Data.csv"

class PredictionModel:

    # Method for get data from database
    def getData(self):
        # MongoDB connection
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_DATA_TABLE]
        collection2 = db[COLLECTION_DATA_TABLE_MAPPING]

        all_data_cursor = collection.find({})
        all_data_cursor2 = collection2.find({})
        
        all_data_list = list(all_data_cursor)
        all_data_list2 = list(all_data_cursor2)

        if all_data_list and all_data_list2:
            # Convert ObjectId to string for serialization for each document
            for data in all_data_list:
                data['_id'] = str(data['_id'])
                
            for data in all_data_list2:
                data['_id'] = str(data['_id'])

            # Convert data to DataFrame
            df = pd.DataFrame(all_data_list)
            df2 = pd.DataFrame(all_data_list2)

            # Drop the _id column
            df = df.drop(columns='_id')
            df2 = df2.drop(columns='_id')

            # Save DataFrame to CSV string
            csv_filename = "./Doctor_Data.csv"
            df.to_csv(csv_filename, index=False)
            
            csv_filename2 = "./Doctor_Data_MIX.csv"
            df2.to_csv(csv_filename2, index=False)

            print(f"{csv_filename} Saved")
            print(f"{csv_filename2} Saved")
        else:
            return None

    # Method for Generate Model
    def generateModel(self):
        df = pd.read_csv(CSV_FILE)

        le_Medicine = LabelEncoder()
        df['Medicine_encoded'] = le_Medicine.fit_transform(df['Prescriptions'])

        le_Notes = LabelEncoder()
        df['Notes_encoded'] = le_Notes.fit_transform(df['Advice'])

        le_Diagnosis = LabelEncoder()
        df['Diagnosis_encoded'] = le_Diagnosis.fit_transform(df['Diagnosis'])

        # Write the updated DataFrame back to the same CSV file
        df.to_csv(CSV_FILE, index=False)    

        Symptom_Medicine = df[['Symptom_ID','Doctor_ID']] # Medicine
        Symptom_Notes = df[['Symptom_ID','Doctor_ID']] # Notes
        Symptom_Diagnosis = df[['Symptom_ID','Doctor_ID']] # Diagnosis

        Symptom_Medicine_df = pd.DataFrame(Symptom_Medicine) # Medicine
        Symptom_Notes_df = pd.DataFrame(Symptom_Notes) # Notes
        Symptom_Diagnosis_df = pd.DataFrame(Symptom_Diagnosis) # Diagnosis

        Answer_Medicine = df['Medicine_encoded'] # Ans Medicine
        Answer_Notes = df['Notes_encoded'] # Ans Notes
        Answer_Diagnosis = df['Diagnosis_encoded'] # Ans Diagnosis

        Symptom_Medicine_train, Symptom_Medicine_test, Answer_Medicine_train, Answer_Medicine_test = train_test_split(Symptom_Medicine_df, Answer_Medicine, test_size=0.25, random_state=42)
        Symptom_Notes_train, Symptom_Notes_test, Answer_Notes_train, Answer_Notes_test = train_test_split(Symptom_Notes_df, Answer_Notes, test_size=0.25, random_state=42)
        Symptom_Diagnosis_train, Symptom_Diagnosis_test, Answer_Diagnosis_train, Answer_Diagnosis_test = train_test_split(Symptom_Diagnosis_df, Answer_Diagnosis, test_size=0.25, random_state=42)

        # Model For Medicine
        model_med = RandomForestClassifier(n_estimators = 100)
        model_med.fit(Symptom_Medicine_train, Answer_Medicine_train)

        # Model For Notes
        model_not = RandomForestClassifier(n_estimators = 100)
        model_not.fit(Symptom_Notes_train, Answer_Notes_train)

        # Model For diagnosis
        model_dig = RandomForestClassifier(n_estimators = 100)
        model_dig.fit(Symptom_Diagnosis_train, Answer_Diagnosis_train)

        # Pickle File for Prediction
        model_medicine_file = open('main_medicine.pkl', 'wb')
        model_notes_file = open('main_notes.pkl', 'wb') 
        model_diagnosis_file = open('main_diagnosis.pkl', 'wb')

        le_medicine_file = open('main_le_medicine.pkl', 'wb')
        le_notes_file = open('main_le_notes.pkl', 'wb')
        le_diagnosis_file = open('main_le_diagnosis.pkl', 'wb')

        # dump information to that file of model
        pickle.dump(model_med, model_medicine_file)
        pickle.dump(model_not, model_notes_file)
        pickle.dump(model_dig, model_diagnosis_file)

        # dump information to that file of encoder
        pickle.dump(le_Medicine, le_medicine_file)
        pickle.dump(le_Notes, le_notes_file)
        pickle.dump(le_Diagnosis, le_diagnosis_file)

        model_medicine_file.close()
        model_notes_file.close()
        model_diagnosis_file.close()

        le_medicine_file.close()
        le_notes_file.close()
        le_diagnosis_file.close()
        
        
# *************************************************************************************        
        
# Method for Create Symptom name dict
# def symptomDict(self):
#     symptom_dict = {}
#     with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
#         reader = csv.DictReader(file)
#         for row in reader:
#             symptom_id = int(row['Symptom_ID'])
#             symptom_name = row['Symptom']
#             # Check if the symptom ID is already in the dictionary
#             if symptom_id not in symptom_dict:
#                 symptom_dict[symptom_id] = symptom_name
#     return symptom_dict