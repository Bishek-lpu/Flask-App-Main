from flask import Flask, request, jsonify
from instamojo_wrapper import Instamojo
from pymongo.mongo_client import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
os.getenv("API_KEY")


api = Instamojo(api_key=os.getenv("API_KEY"),auth_token=os.getenv("AUTH_TOKEN"))
app = Flask(__name__)




class DataBase():
    def __init__(self):
        Username = os.getenv("DB_USERNAME")
        Password = os.getenv("DB_PASSWORD")
        self.__uri_db = f"mongodb+srv://{Username}:{Password}@cluster0.rg4pbtc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.__db = False

    @property
    def userDB(self):
        self.client_read = MongoClient(self.__uri_db )
        self.__db = True
        user_db = self.client_read["ApnaDB"]
        read_collection = user_db["UserData"]
        return read_collection

    def close(self):
        if self.__db :
            self.client_read.close()
            self.__db = False

    def uploadData(self,data:dict):
        query = {'UniqueCode':data.get('UniqueCode')}
        update = {'$set': data }
        result:dict = self.userDB.find_one_and_update(query,update,return_document=True)
        self.close()
        # Check if a document was updated and print it
        if result:
            pass
            # print("Updated document:", result)
        else:
            insert_doc = self.userDB.insert_one(data)
            self.close()
            # print("No document matched the filter criteria.")



# Create a new Payment
def createNewPayment()->str:
    response = api.payment_request_create(
    amount=os.getenv("AMOUNT"),
    purpose=os.getenv("PURPOSE"),
    webhook=os.getenv("WEBHOOK"),
    allow_repeated_payments = False
    )
    if response['success']:
        return response['payment_request']
    

def getPaymentStatus(payment_request_id):
    response = api.payment_request_status(payment_request_id)
    return response



@app.route('/')
def home():
    return "Welcome to the Home Page!"

# Define the first route
@app.route('/Apna-Browser/Initialize-Payment', methods=['POST'])
def InitializePayment():
    db = DataBase()
    # # Get JSON data from the incoming request
    Webhook = None
    data:dict = request.json
    payment_request = createNewPayment()
    
    data.update(payment_request)
    db.uploadData(data)
    db.close()
    responseData = getPaymentStatus((payment_request['id']))

    if responseData['success']:
        Webhook = {'shorturl':responseData['payment_request']['shorturl'], "payment_request_id":responseData['payment_request']["id"]}

    return jsonify({"success": True, "message": Webhook}), 200


# webhook url route
@app.route('/Apna-Browser/Complete-Payment', methods=['POST'])
def CompletePayment():
    # Get JSON data from the incoming request
    try:
        data = request.form.to_dict()  # Instamojo typically sends data in form-encoded format
        # Log or process the webhook data as needed
        print(data)

        payment_id = data.get('payment_id')
        payment_request_id = data.get('payment_request_id')
        status = data.get('status')

        # Process the data based on the payment status
        if status == 'Credit':
            db = DataBase()
            # Update Data Base Payment is Done
            query = {'id':payment_request_id}
            update = {'$set': data }
            result:dict = db.userDB.find_one_and_update(query,update,return_document=False)
            db.close()
        else:
            # Handle payment failure or other statuses
            print(f"Payment {payment_id} failed or is pending.")

        # Respond to Instamojo to confirm receipt
        return jsonify({'status': 'received'}), 200

    except Exception as e:
        # Log the error and return a failure response
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

    


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=False)
