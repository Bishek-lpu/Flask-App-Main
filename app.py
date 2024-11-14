from flask import Flask, request, jsonify
from instamojo_wrapper import Instamojo
from pymongo.mongo_client import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()


api = Instamojo(api_key=os.getenv("API_KEY"),auth_token=os.getenv("AUTH_TOKEN"))
app = Flask(__name__)

def thread_finc(db,data1:dict,payment_request):
    data1.update(payment_request)
    db.uploadData(data1)


def thread_finc2(db,data1:dict):
    payment_request_id = data1.get('payment_request_id') 
    query = {'id':payment_request_id}
    update = {'$set': data1}
    db.userDB.find_one_and_update(query,update,return_document=False)


class DataBase():
    def __init__(self):
        Username = os.getenv("DB_USERNAME")
        Password = os.getenv("DB_PASSWORD")
        self.__uri_db = f"mongodb+srv://{Username}:{Password}@cluster0.rg4pbtc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.client_read = MongoClient(self.__uri_db )
        user_db = self.client_read["ApnaDB"]
        self.read_collection = user_db["UserData"]

    @property
    def userDB(self):
        return self.read_collection


    def uploadData(self,data:dict):
        if data.get('UniqueCode'):
            query = {'UniqueCode':data.get('UniqueCode')}
            update = {'$set': data }
            result:dict = self.userDB.find_one_and_update(query,update,return_document=False)
        # Check if a document was updated and print it
            if not result:
                self.userDB.insert_one(data)

db = DataBase()

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
    # # Get JSON data from the incoming request
    data:dict = request.json
    payment_request = createNewPayment()
    Webhook = {'longurl':payment_request['longurl'], "payment_request_id":payment_request["id"]}
    data.update(payment_request)
    db.uploadData(data)

    return jsonify({"success": True, "message": Webhook}), 200


# webhook url route
@app.route('/Apna-Browser/Complete-Payment', methods=['POST'])
def CompletePayment():
    # Get JSON data from the incoming request
    try:
        data = request.form.to_dict()  # Instamojo typically sends data in form-encoded format
        # Log or process the webhook data as needed

        payment_id = data.get('payment_id')
        status = data.get('status')

        # Process the data based on the payment status
        if status == 'Credit':
            # Update Data Base Payment is Done
            payment_request_id = data.get('payment_request_id') 
            query = {'id':payment_request_id}
            update = {'$set': data}
            db.userDB.find_one_and_update(query,update,return_document=False)
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
    host = "127.0.0.1"
    port = 8080
    app.run(host=host, port=port,debug=False)
    
