from datetime import datetime
from bson import ObjectId



class UserServiceModel:
    def __init__(self, db):
        self.user_services = db.userServices

    def add_service(self, service_data):
        try:
            service_data["createdAt"] = datetime.utcnow()
            service_data["updatedAt"] = datetime.utcnow()
            result = self.user_services.insert_one(service_data)
            return result.inserted_id, None
        except Exception as e:
            return None, str(e)

    def get_all_services(self):
        try:
            services = list(self.user_services.find())
            for service in services:
                service["_id"] = str(service["_id"])
            return services, None
        except Exception as e:
            return None, str(e)