from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils import convert_objectid_to_str, response_with_code

class User:
    def __init__(self, db):
        self.users = db.users
        self.payment = db.payment
        self.partners=db.partners
        self.plots = db.plots  
        
    def create_user(self, user_name, mobile_number, email):
        now = datetime.utcnow()
        result = self.users.insert_one({
            'user_name': user_name,
            'mobile_number': mobile_number,
            'email': email,
            'password': None,
            'userStatus': "Pending",
            'requestType': 'User',
            'isPartner': False,
            'userDisabled': False,            
            'createdAt': now,
            'updatedAt': now,
            "hasCompletedInitialPayment": False,
        })
        return str(result.inserted_id)


    def update_user_disabled_status(self, user_id, status: bool):
        return self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"userDisabled": status, "updatedAt": datetime.utcnow()}}
        )

    def get_all_user(self,user_id):
        return self.users.find({'_id': ObjectId(user_id)})

    def find_by_partnername(self, partner_name):
        return self.users.find_one({'partnerName': partner_name})

    def find_by_email(self, email):
        return self.users.find_one({'email': email})

    def find_user_by_id(self, user_id):
        return self.users.find_one({'_id': ObjectId(user_id)})

    def find_by_username(self, username):
        return self.users.find_one({'username': username})

    def find_by_mobile(self, mobile_number):
        return self.users.find_one({'mobile_number': mobile_number})

    def find_by_id(self, user_id):
        return self.users.find_one({'_id': ObjectId(user_id)})

    def update(self, filter_dict, update_dict):
        update_dict['updatedAt'] = datetime.utcnow()
        return self.users.update_one(filter_dict, {"$set": update_dict})

    def update_one(self, filter_dict, update_dict):
        update_dict['updatedAt'] = datetime.utcnow()
        return self.users.update_one(filter_dict, {'$set': update_dict})

    def check_password(self, stored_password, provided_password):
        return check_password_hash(stored_password, provided_password)

    def store_otp(self, email, otp):
        if otp:
            update_data = {'otp': otp, 'otp_created_at': datetime.utcnow()}
            result = self.users.update_one({'email': email}, {'$set': update_data})
        else:
            result = self.users.update_one({'email': email}, {'$unset': {'otp': "", 'otp_created_at': ""}})
        return result.modified_count == 1

    def update_password(self, email, new_password):
        hashed = generate_password_hash(new_password)
        result = self.users.update_one(
            {'email': email},
            {'$set': {'password': hashed, 'passwordChanged': True, 'updatedAt': datetime.utcnow()}}
        )
        return result.modified_count == 1

    def find_by_otp(self, otp):
        return self.users.find_one({"otp": otp})
    
    def update_user_status_accepted(self, user_id, username, password):
        result = self.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'userStatus': 'Accepted',
                'username': username,
                'password': password,
                'updatedAt': datetime.utcnow()
            }}
        )
        return result.modified_count > 0

    def update_user_status_declined(self, user_id):
        self.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'userStatus': 'Declined', 'updatedAt': datetime.utcnow()}}
        )

    def find_pending_users(self):
        users = list(self.users.find({"userStatus": "Pending"}))
        for user in users:
            user['_id'] = str(user['_id'])
            user['userName'] = user.get('user_name')
            user['mobileNumber'] = user.get('mobile_number')
        return users

    def get_last_approved_user(self):
        return self.users.find_one(
            {"username": {"$regex": r"^500550\d{2}5$"}},
            sort=[("username", -1)]
        )


    def find_all(self):
        return list(self.users.find({}))

    def find_payment_by_user_id(self, user_id):
        return self.payment.find_one({'userId': ObjectId(user_id)})
    
    def find_partner_by_user_id(self, user_id):
        return self.partners.find_one({'userId': ObjectId(user_id)})
        
    def has_sent_credentials(self, user_id):
        user = self.find_user_by_id(user_id)
        return user.get('credentialsSent', False)


    def find_user_by_id(self, user_id):
        return self.users.find_one({"_id": ObjectId(user_id)})

    def update_user_by_id(self, user_id, update_data):
        update_data["updatedAt"] = datetime.utcnow()  # Optional: auto-update timestamp
        return self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
    def generate_next_partner_name(self):
        last_user = self.users.find_one(
            {"partnerName": {"$regex": r"^50055\d+$"}},
            sort=[("partnerName", -1)]
        )
        if last_user and last_user.get("partnerName"):
            last_num = int(last_user["partnerName"])
            return str(last_num + 1)
        return "500551"

    def assign_partner_name(self, user_id):
        new_partner_name = self.generate_next_partner_name()
        self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"partnerName": new_partner_name}}
        )
        return new_partner_name

    def get_last_plot_number(self):
        user = self.users.find_one(
            {"plots": {"$regex": "^P\\d{4}$"}},
            sort=[("plots", -1)]
        )
        return user.get("plots") if user else None
    
    def find_plots_by_user_id(self, user_id):
        return list(self.plots.find({"userId": ObjectId(user_id)}))
    
    def delete_user(self, user_id):
        return self.users.delete_one({"_id": ObjectId(user_id)})
    
    
    def delete_user_by_id(self, user_id):
        return self.users.delete_one({"_id": ObjectId(user_id)})
    
    def update_user_by_id(self, user_id, update_data):
        update_data["updatedAt"] = datetime.utcnow()  
        return self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )