from app.model_controller.service_provider_model import ServiceProvide
from app.utils import convert_objectid_to_str, validate_password,generate_otp,send_emi_confirmation_email,send_credentials_email,send_pending_payment_email,response_with_code,send_email
import random
from datetime import datetime,timedelta
from bson import ObjectId
from app.model_controller.auth_model import User
import string
from flask import render_template
from werkzeug.security import generate_password_hash, check_password_hash

class ServiceProvideModel:
    def __init__(self, db):
        self.service_provider_model = ServiceProvide(db)
        self.auth_model=User(db)


    def register_service(self,data):
        try:
            if not validate_password(data.password):
                return True, "Provided password does not meet requirements"

            if self.service_provider_model.find_by_email(data.email):
                return None, "User already exists"

            service_id = self.service_provider_model.create_service(data)
            return service_id, None

        except Exception as e:
            return None, str(e)
        
    def service_login(self, email, password):
        service = self.service_provider_model.find_by_email(email)
        if service and self.service_provider_model.check_password(service['password'], password):
            return service, None
        if not service:
            return False, "User not found"
        if not self.service_provider_model.check_password(service['password'], password):
            return False, "Password is incorrect"

    def update_service_status(self, service_id, status):
        self.service_provider_model.update_status(service_id, status)


    def service_forgot_password(self, service_id, email):
        service = self.service_provider_model.find_by_service_id(service_id)
        if not service or service.get('email') != email:
            return None, "service not found or email mismatch"

        otp = generate_otp()
        self.service_provider_model.store_otp(service_id, otp)
        send_otp_email(email, otp)
        return otp, None

    def find_admin_by_email(self, email):
        return self.service_provider_model.find_by_email(email)

    def generate_otp(self, length=6):
        return ''.join(str(random.randint(0, 9)) for _ in range(length))

    def update_password(self, email, new_password):
        return self.service_provider_model.update_password(email, new_password)

    def find_user_by_otp(self, otp):
        return self.service_provider_model.find_by_otp(otp)

    def verify_otp(self, service, otp, expiry_minutes=15):
        if not service.get('otp') or not service.get('otp_created_at'):
            return False
        if service['otp'] != otp:
            return False
        otp_age = datetime.utcnow() - service['otp_created_at']
        if otp_age > timedelta(minutes=expiry_minutes):
            return False
        return True

    def update_password(self, user_id, new_password):
        return self.service_provider_model.update_password(user_id, new_password)

    def store_otp(self, user_id, otp):
        return self.service_provider_model.store_otp(user_id, otp)

    def get_all(self, user_id):
        try:
            data = self.service_provider_model.get_user_and_payment(user_id)
            if not data['user']:
                return response_with_code(404, "User not found")

            return response_with_code(200, "User and payment data fetched", data)
        except Exception as e:
            return response_with_code(500, f"Server error: {str(e)}")
