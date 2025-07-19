from flask import request, current_app, jsonify, session 
from app.service_controller.admin_service import AdminService
from app.service_controller.auth_service import AuthService
from app.service_controller.payment_service import PaymentService
from app.service_controller.partner_service import PartnerService
from pydantic import BaseModel, EmailStr, ValidationError,constr
from app.utils import response_with_code,generate_otp,send_otp_email,convert_objectid_to_str
from app.auth_controller.auth import AuthService
from bson.objectid import ObjectId
from datetime import datetime 
import pytz
from app.service_controller.plot_service import PlotService

class AdminSchema(BaseModel):
    email: EmailStr
    adminId:str
    password:str
    mobileNumber:int

class LoginSchema(BaseModel):
    email:str
    password:str

class Change_PasswordSchema(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

class ForgotPasswordSchema(BaseModel):
    email: EmailStr

class ResetPasswordSchema(BaseModel):
    otp: constr(min_length=6, max_length=6)
    new_password:str
    confirm_password:str

class HandleRequestSchema(BaseModel):
    userId: str
    action: str

def admin_create():
    try:
        data = AdminSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400,e.errors()) 

    admin_service = AdminService(current_app.db)
    admin_id, error = admin_service.register_user(data)
    if error:
        return response_with_code(400, error)
    return response_with_code(200, "Admin created successfully") 

def admin_login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return response_with_code(400, "Missing email or password")
    except:
        return response_with_code(400, "Invalid request body")

    admin_service = AdminService(current_app.db)
    admin, error = admin_service.Admin(email, password)

    if error:
        return response_with_code(400, error)

    admin['email'] = email
    admin = convert_objectid_to_str(admin)
    return response_with_code(200, "Admin Logged in Successfully", admin)

def admin_logout():
    admin_id = session.get("admin_id")

    # Clear session
    session.clear()

    # Set admin status to "inactive"
    if admin_id:
        admin_service = AdminService(current_app.db)
        admin_service.update_admin_status(admin_id, "inactive")

    return response_with_code(200, "Admin logged out successfully")
    
def validate_admin_id():
    try:
        admin_id = request.args.get('admin_id')  # <-- fetch from query string
        db = current_app.db
        admin = db.admin.find_one({"_id": ObjectId(admin_id)})
        if not admin:
            return response_with_code(404, "Admin ID not found")
        return response_with_code(200, "Valid Admin", {"adminId": str(admin["_id"])})
    except:
        return response_with_code(400, "Invalid Admin ID format")    
        
def change_password():
    try:
        data = Change_PasswordSchema(**request.get_json())
        admin_id = request.args.get("_id")
        if not admin_id:
            return response_with_code(400, "Missing adminId in query parameter")
    except ValidationError as e:
        return response_with_code(400, e.errors())

    admin_service = AdminService(current_app.db)
    result, error = admin_service.change_password(admin_id, data)
    if error:
        return response_with_code(400, error)
    return response_with_code(200, "Password changed successfully",result)

def forgot_password():
    try:
        data = ForgotPasswordSchema(**request.get_json())
    except ValidationError as e:
    
        return response_with_code(400, "Validation error", e.errors())

    admin_service = AdminService(current_app.db)
    admin = admin_service.find_admin_by_email(data.email)
    if not admin:
        return response_with_code(400, "Admin not found")

    otp = admin_service.generate_otp()
    print(f"Sending OTP {otp} to {data.email}")

    success, err = send_otp_email(data.email, otp)
    if not success:
        return response_with_code(500, "Failed to send OTP", err)

    admin_service.store_otp(admin['_id'], otp)
    return response_with_code(200, "OTP sent successfully")
    
def reset_password():
    try:
        data = ResetPasswordSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400, "Validation error", e.errors())

    if data.new_password != data.confirm_password:
        return response_with_code(400, "Passwords do not match")

    admin_service = AdminService(current_app.db)

    admin = admin_service.find_user_by_otp(data.otp)
    if not admin or not admin_service.verify_otp(admin, data.otp):
        return response_with_code(400, "Invalid or expired OTP")

    success = admin_service.update_password(admin['_id'], data.new_password)
    if not success:
        return response_with_code(500, "Failed to update password")

    admin_service.store_otp(admin['_id'], None)  # Clear OTP after reset

    return response_with_code(200, "Password reset successful")

def get_all_login_requests():
    admin_service = AdminService(current_app.db)
    return admin_service.get_all_pending_users()  # ✅ shows all plan types (A, B, C, etc.)

def get_all_plans_requests():
    admin_service = AdminService(current_app.db)
    return admin_service.get_pending_plan_a_b_users()

def get_user_and_payment_data():
    try:
        admin_service = AdminService(current_app.db)
        result = admin_service.get_user_and_payment()
        return response_with_code(200, "User and payment data fetched", result)
    except Exception as e:
        return response_with_code(500, f"Server error: {str(e)}")
    

   
def mark_full_payment():
    try:
        data = request.get_json()
        user_id = data.get("userId")

        if not user_id:
            return response_with_code(400, "Missing userId")

        payment_service = PaymentService(current_app.db)
        return payment_service.mark_payment_complete_and_send_credentials(user_id)

    except Exception as e:
        print(f"Error in mark_full_payment: {e}")
        return response_with_code(500, f"Internal server error: {str(e)}")

def give_monthly_commission():
    data = request.get_json()
    partner_id = data.get("partnerId")
    if not partner_id:
        return response_with_code(400, "Missing partnerId")

    service = PartnerService(current_app.db)
    service.add_monthly_commission(partner_id)
    return response_with_code(200, "Commission added to wallet")

def list_partners():
    service = PartnerService(current_app.db)
    partners = service.list_all_partners()
    return response_with_code(200, "Partner data fetched", partners)

def get_partner_overview():
    service = PartnerService(current_app.db)
    partners = service.get_all_partners_for_admin()
    return response_with_code(200, "Success", partners)

def get_all_collaborators():
    payment_service = PaymentService(current_app.db)
    collaborators = payment_service.get_all_collaborators()

    return response_with_code(200, "Collaborators fetched successfully", collaborators)

def toggle_user_and_partner_status():
    data = request.get_json()
    user_id = data.get("userId")
    disabled = data.get("disabled")

    if not user_id or not isinstance(disabled, bool):
        return response_with_code(400, "Missing userId or invalid disabled status")

    admin_service = AdminService(current_app.db)
    success, message = admin_service.disable_user_and_partner(user_id, disabled)
    if not success:
        return response_with_code(404, message)

    return response_with_code(200, message)

def admin_approve_plot_payment():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        plot_id = data.get("plot_id")

        if not user_id or not plot_id:
            return response_with_code(400, "Missing user_id or plot_id")

        plot_service = PlotService(current_app.db)
        result, error = plot_service.approve_plot_payment(user_id, plot_id)

        if error:
            return response_with_code(400, error)

        return response_with_code(200, "Plot payment approved successfully", result)
    except Exception as e:
        return response_with_code(500, f"Internal server error: {str(e)}")
    
def handle_user_request():
    try:
        data = request.get_json()
        user_id = data.get("userId")
        action = data.get("action")
        plan_type = data.get("planType")  

        if not user_id or action not in ["Accepted", "Ignored"]:
            return response_with_code(400, "Invalid user ID or action")

        if action == "Accepted" and not plan_type:
            payment = current_app.db.payment.find_one({"userId": ObjectId(user_id)})
            plan_type = payment.get("initialPlanType") if payment else None

            if not plan_type:
                return response_with_code(400, "Plan type not found for user")

        admin_service = AdminService(current_app.db)

        if action == "Accepted":
            return admin_service.approve_user(user_id, plan_type)
        elif action == "Ignored":
            return admin_service.decline_user(user_id)

        return response_with_code(400, "Unknown action")

    except Exception as e:
        print(e)
        return response_with_code(500, f"Internal server error: {str(e)}")
    
def admin_decline_plot():
    data = request.get_json()
    plot_id = data.get("plot_id")

    if not plot_id:
        return response_with_code(400, "Missing plot_id")

    plot_service = PlotService(current_app.db)
    result, error = plot_service.decline_plot(plot_id)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "Plot request declined successfully", result)
# def handle_user_request():
#     try:
#         data = request.get_json()
#         user_id = data.get("userId")
#         action = data.get("action")
#         plan_type = data.get("initialPlanType")  

#         if not user_id or action not in ["Accepted", "Ignored"]:
#             return response_with_code(400, "Invalid user ID or action")

#         admin_service = AdminService(current_app.db)

#         if action == "Accepted":
#             return admin_service.approve_user(user_id, plan_type)
#         elif action == "Ignored":
#             return admin_service.decline_user(user_id)

#         # 🚨 Fallback return to prevent None being returned
#         return response_with_code(400, "Unknown action")

#     except Exception as e:
#         return response_with_code(500, f"Internal server error: {str(e)}")  