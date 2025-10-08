from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
from app.utils import convert_objectid_to_str

class Admin:
    def __init__(self, db):
        self.admin = db.admin
        self.users = db.users         
        self.payment = db.payment
        self.partners = db.partners
        self.plots = db.plots

    def create_admin_user(self, data):
        password_hash = generate_password_hash(data.password, method='pbkdf2:sha512')
        now = datetime.utcnow()
        status = "inactive"
        admin_data = {
            "email": data.email,
            "mobileNumber": data.mobileNumber,
            "adminName": data.adminName,
            "password": password_hash,
            "status": status,
            "createdAt": now,
            "updatedAt": now
        }
        result = self.admin.insert_one(admin_data)
        return result.inserted_id

    def find_by_email(self, email):
        admin = self.admin.find_one({"email": email})
        if admin:
            admin["_id"] = str(admin["_id"])
        return admin

    def update_status(self, admin_id, status):
        self.admin.update_one(
            {"_id": ObjectId(admin_id)},
            {"$set": {
                "status": status,
                "updatedAt": datetime.utcnow()
            }}
        )

    @staticmethod
    def check_password(stored_password, provided_password):
        return check_password_hash(stored_password, provided_password)

    def find_by_id(self, adminId):
        result = self.admin.find_one({'adminId': adminId})
        return  result

    def find_by_admin_id(self, adminId):
        result = self.admin.find_one({'_id':ObjectId(adminId)})
        return  result

    def update_password(self, admin_id, new_password):
        hashed = generate_password_hash(new_password, method='pbkdf2:sha512')
        result = self.admin.update_one(
            {'_id':ObjectId(admin_id)},
            {'$set': {'password': hashed, 'updatedAt': datetime.utcnow()}}
        )
        return result.modified_count > 0

    def store_otp(self, admin_id, otp):
        self.admin.update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': {'otp': otp, 'otp_created_at': datetime.utcnow()}}
        )

    def clear_otp(self, admin_id):
        self.admin.update_one(
            {'_id':ObjectId(admin_id)},
            {'$unset': {'otp': "", 'otp_created_at': ""}}
        )
    
    def find_by_email(self, email):
        return self.admin.find_one({'email': email})

    def update_one(self, filter_dict, update_dict):
        update_dict['updatedAt'] = datetime.utcnow()
        return self.admin.update_one(filter_dict, {'$set': update_dict})

    def find_by_otp(self, otp):
        return self.admin.find_one({"otp": otp})

    def get_all_admin_emails(self):
        admins = self.admin.find({}, {'email': 1})
        return [admin['email'] for admin in admins if 'email' in admin]

    def get_user_and_payment(self):
            users = list(self.users.find({}))
            user_ids = [user['_id'] for user in users]

            # Fetch all related documents
            payments = list(self.payment.find({"userId": {"$in": user_ids}}))
            payment_map = {p['userId']: p for p in payments}

            partners = list(self.partners.find({"userId": {"$in": user_ids}}))
            partner_map = {p['userId']: p for p in partners}

            plots = list(self.plots.find({"userId": {"$in": user_ids}}))

            result = []
            for user in users:
                user_id = user['_id']
                user.pop("password", None)

                # Collect all plots for this user
                user_plots = [p for p in plots if p["userId"] == user_id]

                result.append({
                    "user": user,
                    "payment": payment_map.get(user_id, {}),
                    "partner": partner_map.get(user_id, {}),
                    "plots": user_plots  # Now this is a list of plot objects
                })

            return result