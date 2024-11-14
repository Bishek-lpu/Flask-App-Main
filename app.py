from flask import Flask, request, jsonify
from instamojo_wrapper import Instamojo
from pymongo.mongo_client import MongoClient
from pymongo import ReturnDocument
from threading import Thread
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Initialize Flask app and Instamojo API
app = Flask(__name__)
api = Instamojo(api_key=os.getenv("API_KEY"), auth_token=os.getenv("AUTH_TOKEN"))

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)

class DataBase:
    def __init__(self):
        username = os.getenv("DB_USERNAME")
        password = os.getenv("DB_PASSWORD")
        self.__uri_db = (
            f"mongodb+srv://{username}:{password}@cluster0.rg4pbtc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&maxPoolSize=10"
        )
        self.client = MongoClient(self.__uri_db)
        user_db = self.client["ApnaDB"]
        self.collection = user_db["UserData"]

    def upload_data(self, data: dict):
        try:
            query = {'UniqueCode': data.get('UniqueCode')}
            update = {'$set': data}
            result = self.collection.find_one_and_update(query, update, upsert=True, return_document=ReturnDocument.AFTER)
            logging.info("Data uploaded or updated successfully.")
            return result
        except Exception as e:
            logging.error(f"Error in upload_data: {e}")
            return None

    def update_payment_status(self, data: dict):
        try:
            payment_request_id = data.get('payment_request_id')
            query = {'id': payment_request_id}
            update = {'$set': data}
            result = self.collection.find_one_and_update(query, update, return_document=ReturnDocument.AFTER)
            logging.info("Payment status updated successfully.")
            return result
        except Exception as e:
            logging.error(f"Error in update_payment_status: {e}")
            return None

db = DataBase()

# Helper function to create a new payment
def create_new_payment() -> dict:
    try:
        response = api.payment_request_create(
            amount=os.getenv("AMOUNT"),
            purpose=os.getenv("PURPOSE"),
            webhook=os.getenv("WEBHOOK"),
            allow_repeated_payments=False
        )
        if response['success']:
            logging.info("Payment request created successfully.")
            return response['payment_request']
        else:
            logging.error("Failed to create payment request.")
            return {}
    except Exception as e:
        logging.error(f"Error in create_new_payment: {e}")
        return {}

# Route to initialize payment
@app.route('/Apna-Browser/Initialize-Payment', methods=['POST'])
def initialize_payment():
    data = request.json
    payment_request = create_new_payment()
    
    if payment_request:
        webhook = {'longurl': payment_request['longurl'], "payment_request_id": payment_request["id"]}
        data.update(payment_request)
        
        # Start thread for data upload
        thread = Thread(target=db.upload_data, args=(data,))
        thread.start()
        
        return jsonify({"success": True, "message": webhook}), 200
    else:
        return jsonify({"success": False, "message": "Failed to create payment request"}), 500

# Webhook route to complete payment
@app.route('/Apna-Browser/Complete-Payment', methods=['POST'])
def complete_payment():
    try:
        data = request.form.to_dict()  # Instamojo sends data in form-encoded format
        payment_id = data.get('payment_id')
        status = data.get('status')
        
        if status == 'Credit':
            # Start thread for payment status update
            thread = Thread(target=db.update_payment_status, args=(data,))
            thread.start()
        else:
            logging.info(f"Payment {payment_id} failed or is pending.")
        
        return jsonify({'status': 'received'}), 200

    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

# Home route
@app.route('/')
def home():
    return "Welcome to the Home Page!"

# Run the Flask app
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
