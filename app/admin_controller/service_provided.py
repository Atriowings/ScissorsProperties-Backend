from flask import request, current_app ,session
from app.service_controller.service_provided_service import ServiceProvideModel
from app.service_controller.coupen_service import CouponService
from pydantic import BaseModel, EmailStr, ValidationError,constr
from app.utils import response_with_code,generate_otp,send_otp_email,convert_objectid_to_str,is_session_expired
from bson.objectid import ObjectId
from datetime import datetime 
import pytz

class ServiceSchema(BaseModel):
    email: EmailStr
    serviceName:str
    password:str
    mobileNumber:int

class ServiceLoginSchema(BaseModel):
    email:str
    password:str

class ForgotPasswordServiceSchema(BaseModel):
    email: EmailStr

class ResetPasswordServiceSchema(BaseModel):
    otp: constr(min_length=6, max_length=6)
    new_password:str
    confirm_password:str


def service_create():
    try:
        data = ServiceSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400,e.errors()) 

    service_provided_service = ServiceProvideModel(current_app.db)
    service_id, error = service_provided_service.register_service(data)
    if error:
        return response_with_code(400, error)
    return response_with_code (200, "Service created successfully") 

def service_login():
    try:
        data = ServiceLoginSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400, e.errors())

    service_provided_service = ServiceProvideModel(current_app.db)
    service, error = service_provided_service.service_login(data.email, data.password)

    if error:
        return response_with_code(400, error)

    service['_id'] = str(service['_id'])
    # Set service session
    # session.permanent = True
    session['service_logged_in'] = True
    session['service_id'] = service['_id']
    session['service_email'] = service['email']
    session['login_time'] = datetime.utcnow().isoformat() 

    # Update service status to "active"
    service_provided_service.update_service_status(service['_id'], "active")

    service.pop('password', None)
    service = convert_objectid_to_str(service)

    return response_with_code(200, "service Logged in Successfully", service)

def service_logout():
    service = ServiceProvideModel(current_app.db)
    service_id = session.get("service_id")

    # Handle expired session
    if is_session_expired():
        if service_id:
            service.update_service_status(service_id, "inactive")
        session.clear()
        return response_with_code(401, "Session expired. service logged out.")

    # Valid logout
    if service_id:
        service.update_service_status(service_id, "inactive")
    session.clear()
    return response_with_code(200, "service logged out successfully")

def service_forgot_password():
    try:
        data = ForgotPasswordServiceSchema(**request.get_json())
    except ValidationError as e:
    
        return response_with_code(400, "Validation error", e.errors())

    service_provided_service = ServiceProvideModel(current_app.db)
    admin = service_provided_service.find_admin_by_email(data.email)
    if not admin:
        return response_with_code(400, "Admin not found")

    otp = service_provided_service.generate_otp()
    print(f"Sending OTP {otp} to {data.email}")

    success, err = send_otp_email(data.email, otp)
    if not success:
        return response_with_code(500, "Failed to send OTP", err)

    service_provided_service.store_otp(admin['_id'], otp)
    return response_with_code(200, "OTP sent successfully")
    
def service_reset_password():
    try:
        data = ResetPasswordServiceSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400, "Validation error", e.errors())

    if data.new_password != data.confirm_password:
        return response_with_code(400, "Passwords do not match")

    service_provided_service = ServiceProvideModel(current_app.db)

    service = service_provided_service.find_user_by_otp(data.otp)
    if not service or not service_provided_service.verify_otp(service, data.otp):
        return response_with_code(400, "Invalid or expired OTP")

    success = service_provided_service.update_password(service['_id'], data.new_password)
    if not success:
        return response_with_code(500, "Failed to update password")

    service_provided_service.store_otp(service['_id'], None) 

    return response_with_code(200, "Password reset successful")

def get_all_login_coupons():
    admin_service = ServiceProvideModel(current_app.db)
    return admin_service.get_all_pending_users() 


def generate_service_coupon():
    data = request.get_json()
    user_id = data.get("userId")
    service_name = data.get("serviceName")
    price = data.get("price")

    if not user_id or not service_name or not price:
        return response_with_code(400, "Missing required fields")

    service = CouponService(current_app.db)
    result, error = service.generate_coupon(user_id, service_name, price)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "Coupon generated successfully", result)

# Coupon usage
def use_coupon():
    data = request.get_json()
    coupon_code = data.get("couponCode")

    if not coupon_code:
        return response_with_code(400, "Coupon code required")

    service = CouponService(current_app.db)
    success, error = service.mark_coupon_used(coupon_code)

    if error:
        return response_with_code(500, error)

    return response_with_code(200, "Coupon used and removed from all records")