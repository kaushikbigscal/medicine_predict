from flask import request, Flask, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import pickle
import csv
import time
from model import PredictionModel
import os
import re
from collections import Counter

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "headers": "Content-Type"}})

# Variable For Store Data Of Payloads
SYMPTOM_ID = []
DOCTOR_ID = []
DIAGNOSIS_ID = []

CSV_FILE = ['Doctor_Data.csv','Doctor_Data_MIX.csv']
FILE = 'Doctor_Data_MIX.csv'

# Create Object For Prediction Model
PREDICTION_MODEL = PredictionModel()

# Method for checking CSV_FILE is exist or not
def check_files_exist(file_paths):
    print(file_paths)
    for file_path in file_paths:
        if not os.path.exists(file_path):
            return False
    return True

if not check_files_exist(CSV_FILE):

    PREDICTION_MODEL.getData()
    time.sleep(5)

if check_files_exist(CSV_FILE):

    MAIN_MODEL = PREDICTION_MODEL.generateModel()

# Variable for checking pkl file exixt or not 
pickle_files = [
        'main_medicine.pkl', 
        'main_notes.pkl', 
        'main_diagnosis.pkl', 
        'main_le_notes.pkl', 
        'main_le_medicine.pkl', 
        'main_le_diagnosis.pkl'
    ]

# Function For Load All Pickle File
def load_models_and_encoders():
    
    if not check_files_exist(pickle_files):
        print("Some pickle files are missing.")
        return None
    
    with open('main_medicine.pkl', 'rb') as f:
        model_medicine = pickle.load(f)
    with open('main_notes.pkl', 'rb') as f:
        model_notes = pickle.load(f)
    with open('main_diagnosis.pkl', 'rb') as f:
        model_diagnosis = pickle.load(f)
    with open('main_le_notes.pkl', 'rb') as f:
        le_notes = pickle.load(f)
    with open('main_le_medicine.pkl', 'rb') as f:
        le_medicine = pickle.load(f)
    with open('main_le_diagnosis.pkl', 'rb') as f:
        le_diagnosis = pickle.load(f)

    return {
        'model_medicine': model_medicine,
        'model_notes': model_notes,
        'model_diagnosis': model_diagnosis,
        'le_notes': le_notes,
        'le_medicine': le_medicine,
        'le_diagnosis': le_diagnosis
    }

# Create Object Of load_models_and_encoders()
loaded_models_and_encoders = load_models_and_encoders()

if loaded_models_and_encoders is not None:
    # Variable Of All Pickle File
    MODEL_MEDICINE = loaded_models_and_encoders['model_medicine']
    MODEL_NOTES = loaded_models_and_encoders['model_notes']
    MODEL_DIAGNOSIS = loaded_models_and_encoders['model_diagnosis']
    LE_NOTES = loaded_models_and_encoders['le_notes']
    LE_MEDICINE = loaded_models_and_encoders['le_medicine']
    LE_DIAGNOSIS = loaded_models_and_encoders['le_diagnosis']

# Main API
@app.route('/medicinePrediction/get_medicine', methods=['POST', 'GET'])
def medicinePrediction():
    global data, doctor_ids

    json_data = request.get_json()
    request_data = json_data["data"]

    # Ensure that required fields are present in the request
    if 'symptom_id' not in request_data:
        return jsonify({'error': 'Missing required fields.'}), 400

    # Extract values from request data
    SYMPTOM_ID = request_data.get('symptom_id')
    DOCTOR_ID = request_data.get('doctor_id', [])

    # Ensure DOCTOR_ID is a list
    doctor_ids = DOCTOR_ID if isinstance(DOCTOR_ID, list) else [DOCTOR_ID]

    # First Map Data if All Symptoms Properly Match 
    diagnosis, advice, prescriptions, status, success, message = Map.map_data(doctor_ids, SYMPTOM_ID)

    # If any of diagnosis, advice, or prescriptions is None, call prediction method
    if not diagnosis or not advice or not prescriptions:
        med_probs, notes_probs, diag_probs, status, success, message = prediction(SYMPTOM_ID, doctor_ids)
    else:
        med_probs, notes_probs, diag_probs = None, None, None


    # Construct the response data based on the conditions
    data = {
        'Medicine': list(set(prescriptions if prescriptions else med_probs)),
        'Advice': list(set(advice if advice else notes_probs)),
        'Diagnosis': list(set(diagnosis if diagnosis else diag_probs))
    }

    # Return Response
    return jsonify({
        "status": status,
        "statusState": success,
        "message": message,
        'data': data,
    }), 200


# Main Prediction Method
def prediction(ids, doctor_ids):
    # Load CSV file
    csv_file_path = "./Doctor_Data.csv"
    
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        
        # Convert Into List
        symptom_name_set = list(set(ids))

        # Initialize lists to store predictions for each symptom
        predicted_notes_encoded_list = []
        predicted_medicine_encoded_list = []
        predicted_diagnosis_encoded_list = []
        message = []

        # Loop through each symptom
        for doctor_id in doctor_ids:
            for symptom in symptom_name_set:
                doctor_data = df[(df['Doctor_ID'] == doctor_id) & (df['Symptom_ID'] == symptom)]
                if len(doctor_data) == 0:
                    message.append(f"No prediction for symptom {symptom} and doctor {doctor_id}.")
                else:
                    predicted_medicine_encoded_list.extend(
                        MODEL_MEDICINE.predict(doctor_data[['Symptom_ID', 'Doctor_ID']]))
                    predicted_notes_encoded_list.extend(
                        MODEL_NOTES.predict(doctor_data[['Symptom_ID', 'Doctor_ID']]))
                    predicted_diagnosis_encoded_list.extend(
                        MODEL_DIAGNOSIS.predict(doctor_data[['Symptom_ID', 'Doctor_ID']]))

        # reshape lists
        predicted_medicine_encoded_list = np.array(predicted_medicine_encoded_list)
        predicted_notes_encoded_list = np.array(predicted_notes_encoded_list)
        predicted_diagnosis_encoded_list = np.array(predicted_diagnosis_encoded_list)

        # Handle unseen labels
        predicted_medicine_encoded_list = np.where(predicted_medicine_encoded_list < LE_MEDICINE.classes_.shape[0],
                                                predicted_medicine_encoded_list, 0)
        predicted_notes_encoded_list = np.where(predicted_notes_encoded_list < LE_NOTES.classes_.shape[0],
                                                predicted_notes_encoded_list, 0)
        predicted_diagnosis_encoded_list = np.where(predicted_diagnosis_encoded_list < LE_DIAGNOSIS.classes_.shape[0],
                                                    predicted_diagnosis_encoded_list, 0)
        

        # Decode the predictions
        predicted_medicine = LE_MEDICINE.inverse_transform(predicted_medicine_encoded_list)
        predicted_notes = LE_NOTES.inverse_transform(predicted_notes_encoded_list)
        predicted_diagnosis = LE_DIAGNOSIS.inverse_transform(predicted_diagnosis_encoded_list)


        # filtered NaN Value
        filtered_medicine = set([x for x in predicted_medicine if not isinstance(x, float) and x == x])
        filtered_notes = set([x for x in predicted_notes if not isinstance(x, float) and x == x])
        filtered_diagnosis = set([x for x in predicted_diagnosis if x != '()'])
        
        Medicine_ID = list(set(extract_numbers(filtered_medicine)))
        Diagnosis_ID = list(set(extract_numbers(filtered_diagnosis)))
        Notes_ID = list(set(extract_numbers(filtered_notes)))

        return Medicine_ID, Notes_ID, Diagnosis_ID, 200, "success", message
    else:
        print("Model Does Not Exist")

# Extract ID From List
def extract_numbers(data):
    # Regular expression pattern to extract numbers within parentheses
    pattern = r'\((\d+)\)'

    extracted_numbers = []

    # Extract numbers from each string and add them to the list
    for item in data:
        numbers = re.findall(pattern, item)
        extracted_numbers.extend(numbers)

    # Remove duplicates by converting the list to a set
    unique_numbers = set(extracted_numbers)

    return unique_numbers

# Class For Map Data To Data Set
class MappingInputValue:
    
    def __init__(self, data_file):
        self.df = pd.read_csv(data_file)

# Method for Count Sypmtom 
    @staticmethod
    def count_symptoms(entry):
        if isinstance(entry, list):
            return len(entry)
        elif isinstance(entry, str) and entry.strip():
            return len(entry.split(','))
        return 0

# METHOD FOR fILTER IDs
    @staticmethod
    def filter_ids(lst):
        individual_ids = []
        id_pattern = re.compile(r'\((\d+)\)')

        for item in lst:
            if isinstance(item, str):
                medicines = item.split(',')
                for medicine in medicines:
                    individual_ids.extend(id_pattern.findall(medicine))
                    
        counts = Counter(individual_ids)
        repeating_values = [value for value, count in counts.items() if count >= 3] if max(counts.values(), default=0) >= 3 else individual_ids

        return repeating_values

#Method for Map data 
    def map_data(self, doctor_id, symptom_ids):
        if not isinstance(symptom_ids, list):
            return None, None, None, 404, False, "No matching records found"
        
        symptom_ids_set = set(map(str, symptom_ids))
        
        # Filter the DataFrame to get rows with matching Doctor ID
        filtered_df = self.df[self.df['Doctor_ID'].isin(doctor_id) if isinstance(doctor_id, list) else self.df['Doctor_ID'] == doctor_id]

        if filtered_df.empty:
            return None, None, None, 404, False, "No matching records found"

        matched_rows = filtered_df[filtered_df['Symptom_ID'].apply(lambda x: set(map(str, str(x).replace(' ', '').split(','))) == symptom_ids_set)]

        if matched_rows.empty:
            return None, None, None, 404, False, "No matching records found"
        
        # Extract relevant columns
        diagnoses = matched_rows['Diagnosis'].tolist()
        advices = matched_rows['Advice'].tolist()
        prescriptions = matched_rows['Prescriptions'].tolist()

        # Filter IDs from the diagnosis, advice, and prescriptions lists
        diagnoses_filtered = list(set(self.filter_ids(diagnoses)))
        advices_filtered = list(set(self.filter_ids(advices)))
        prescriptions_filtered = list(set(self.filter_ids(prescriptions)))

        return diagnoses_filtered, advices_filtered, prescriptions_filtered, 200, True, "Mapping"

# Create Object of Class MappingInputValue
if check_files_exist(CSV_FILE):
    Map = MappingInputValue(FILE)
    
# Main Function
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6000)  # host='0.0.0.0', port=5000,
    
    
