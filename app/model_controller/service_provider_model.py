from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
from app.utils import convert_objectid_to_str

class ServiceProvide:
    def __init__(self, db):
        self.service = db.service

    def create_service(self, data):
        password_hash = generate_password_hash(data.password, method='pbkdf2:sha512')
        now = datetime.utcnow()
        service_data = {
            "email": data.email,
            "mobileNumber": data.mobileNumber,
            "password": password_hash,
            "serviceName":data.serviceName,
            "status": "inactive",
            "createdAt": now,
            "updatedAt": now,
            "coupens": []
        }
        result = self.service.insert_one(service_data)
        return result.inserted_id

    def find_by_email(self, email):
        service = self.service.find_one({"email": email})
        if service:
            service["_id"] = str(service["_id"])
        return service

    def update_status(self, service_id, status):
        self.service.update_one(
            {"_id": ObjectId(service_id)},
            {"$set": {
                "status": status,
                "updatedAt": datetime.utcnow()
            }}
        )

    @staticmethod
    def check_password(stored_password, provided_password):
        return check_password_hash(stored_password, provided_password)

    def find_by_id(self, ServiceId):
        result = self.service.find_one({'ServiceId': ServiceId})
        return  result

    def find_by_service_id(self, ServiceId):
        result = self.service.find_one({'_id':ObjectId(ServiceId)})
        return  result

    def update_password(self, service_id, new_password):
        hashed = generate_password_hash(new_password, method='pbkdf2:sha512')
        result = self.service.update_one(
            {'_id':ObjectId(service_id)},
            {'$set': {'password': hashed, 'updatedAt': datetime.utcnow()}}
        )
        return result.modified_count > 0

    def store_otp(self, service_id, otp):
        self.service.update_one(
            {'_id': ObjectId(service_id)},
            {'$set': {'otp': otp, 'otp_created_at': datetime.utcnow()}}
        )

    def clear_otp(self, service_id):
        self.service.update_one(
            {'_id':ObjectId(service_id)},
            {'$unset': {'otp': "", 'otp_created_at': ""}}
        )
    
    # def find_by_email(self, email):
    #     return self.service.find_one({'email': email})

    def update_one(self, filter_dict, update_dict):
        update_dict['updatedAt'] = datetime.utcnow()
        return self.service.update_one(filter_dict, {'$set': update_dict})

    def find_by_otp(self, otp):
        return self.service.find_one({"otp": otp})

    def get_all_service_emails(self):
        service = self.service.find({}, {'email': 1})
        return [service['email'] for service in service if 'email' in service]


    # def create_service(self, user_id, service_name, coupon_code):
    #     service_data = {
    #         "userId": ObjectId(user_id),
    #         "serviceName": service_name,
    #         "couponCode": coupon_code,
    #         "couponApplied": True,
    #         "createdAt": datetime.utcnow()
    #     }
    #     return self.service.insert_one(service_data)

    def find_by_user(self, user_id):
        return self.service.find({"userId": ObjectId(user_id)})


    def push_coupon_global(self, user_id, coupon_data):
        coupon_data["userId"] = ObjectId(user_id)
        coupon_data["createdAt"] = coupon_data.get("createdAt", datetime.utcnow())
        coupon_data["used"] = coupon_data.get("used", False)

        return self.service.update_one(
            {},  # Assume only one service document
            {
                "$push": {"coupens": coupon_data},
                "$set": {"updatedAt": datetime.utcnow()}
            }
        )
