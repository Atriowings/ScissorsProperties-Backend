from flask import request, jsonify, current_app, send_file
from pydantic import BaseModel, EmailStr, ValidationError,constr
from flask_jwt_extended import jwt_required
from bson import ObjectId
import qrcode
import io
from app.service_controller.auth_service import AuthService
from app.service_controller.payment_service import PaymentService
from app.utils import send_welcome_email,send_admin_notification_email,send_credentials_email, generate_otp, send_otp_email, response_with_code



class RegisterSchema(BaseModel):
    user_name: str
    mobile_number: int
    email: EmailStr
    referredBy: str  
    referredById: str = None 

class LoginSchema(BaseModel):
    login_input: str
    password: str

class ChangePasswordSchema(BaseModel):
    new_password: str
    confirm_password: str

class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    otp: constr(min_length=6, max_length=6)
    new_password:str
    confirm_password:str

def Signup():
    try:
        data = RegisterSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400, "Validation error", e.errors())

    # Validate referral logic
    referred_by = data.referredBy.lower()
    referral_id = data.referredById

    # Referral ID is required only if referredBy is not "myself" or "no one"
    if referred_by not in ["myself", "no one"] and not referral_id:
        return response_with_code(400, "Referral ID is required for selected referredBy")

    auth_service = AuthService(current_app.db)

    # Validate referral ID if provided
    partner_user_id = None
    if referral_id:
        partner_model = current_app.db.partners
        partner = partner_model.find_one({"myReferralId": referral_id})
        if not partner:
            return response_with_code(400, "Invalid referral ID")
        partner_user_id = partner["userId"]

    # Create user
    user, error = auth_service.signup(data)
    if error:
        return response_with_code(400, error)

    current_app.db.users.update_one(
        {"_id": ObjectId(user['_id'])},
        {"$set": {
            "isEmailVerified": True,
            "referredBy": referred_by,
            "referredById": referral_id
        }}
    )

    # Add user to the referrals list of the referring partner
    if partner_user_id:
        current_app.db.partners.update_one(
            {"userId": ObjectId(partner_user_id)},
            {"$push": {"referrals": ObjectId(user['_id'])}}
        )

    send_welcome_email(data.user_name, [data.email])
    return response_with_code(200, "User registered successfully", str(user['_id']))
    
def Complete_payment():
    data = request.get_json()

    user_id = data.get('user_id')
    plan_type = data.get('planType')
    upi = data.get('upi')
    upi_mobile_number = data.get('upiMobileNumber')

    if not user_id or not plan_type or not upi or not upi_mobile_number:
        return response_with_code(400, "Missing user_id or planType or upi or upiMobileNumber")

    payment_service = PaymentService(current_app.db)
    result, error = payment_service.complete_payment_flow(user_id, plan_type, upi, upi_mobile_number)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "Payment completed. Awaiting admin approval.")

def Login():
    try:
        data = LoginSchema(**request.get_json())
    except ValidationError as e:
        return jsonify({
            "status_code": 400,
            "message": "Validation error",
            "data": e.errors()
        }), 400

    auth_service = AuthService(current_app.db)
    user_id, error = auth_service.signin(data)
    if error:
        return jsonify({"status_code": 400, "message": error}), 400

    user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"status_code": 404, "message": "User not found"}), 404

    return jsonify({
        "status_code": 200,
        "message": "User login successfully",
        "data": {
            "user_id": str(user_id),
            "login_input": data.login_input
        }
    }), 200


def Change_password():
    try:
        data = ChangePasswordSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400, "Validation error", e.errors())

    user_id = request.args.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id in query parameters")
    try:
        object_id = ObjectId(user_id)
    except Exception:
        return response_with_code(400, "Invalid user_id format")
    auth_service = AuthService(current_app.db)
    success, error = auth_service.user_change_password(user_id, data)
    if error:
        return response_with_code(400, error)

    return response_with_code(200, "Password changed successfully")

def Forgot_password():
    try:
        data = ForgotPasswordSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400, "Validation error", e.errors())

    auth_service = AuthService(current_app.db)
    user = auth_service.find_user_by_email(data.email)
    if not user:
        return response_with_code(400, "User not found")

    otp = auth_service.generate_otp()
    print(f"Sending OTP {otp} to {data.email}")

    success, err = send_otp_email(data.email, otp)
    if not success:
        return response_with_code(500, "Failed to send OTP", err)

    auth_service.store_otp(user['email'], otp)
    return response_with_code(200, "OTP sent successfully")
    
def Reset_password():
    try:
        data = ResetPasswordSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400, "Validation error", e.errors())

    if data.new_password != data.confirm_password:
        return response_with_code(400, "Passwords do not match")

    auth_service = AuthService(current_app.db)

    user = auth_service.find_user_by_otp(data.otp)
    if not user:
        return response_with_code(400, "OTP not found")

    if not auth_service.verify_otp(user, data.otp):
        return response_with_code(400, "OTP invalid or expired")

    # ✅ FIXED unpacking issue
    success = auth_service.update_password(user['email'], data.new_password)
    if not success:
        return response_with_code(500, "Failed to update password")

    auth_service.store_otp(user['email'], None)  # Clear OTP

    return response_with_code(200, "Password reset successfully")


def get_lucky_charm_status():
    user_id = request.args.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    payment = current_app.db.payment.find_one({"userId": ObjectId(user_id)})

    if not payment:
        return response_with_code(404, "Payment record not found", {
            "canParticipateLuckyDraw": False,
            "luckyDrawMessage": "No payment found."
        })

    return response_with_code(200, "Lucky charm status retrieved", {
        "canParticipateLuckyDraw": payment.get("canParticipateLuckyDraw", False),
        "luckyDrawMessage": payment.get("luckyDrawMessage", "Eligible")
    })
    
def validate_user_id():
    try:
        user_id = request.args.get('user_id')
        print("Validating user ID:", user_id)  # ✅ Debug print
        db = current_app.db
        user = db.user.find_one({"_id": ObjectId(user_id)})
        if not user:
            return response_with_code(404, "User ID not found")
        return response_with_code(200, "Valid User", {"userId": str(user["_id"])})
    except Exception as e:
        print("Exception in validate_user_id:", e)
        return response_with_code(400, "Invalid User ID format")

def customer_dashboard():
    user_id = request.args.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    auth_service = AuthService(current_app.db)
    return auth_service.get_customer_dashboard(user_id)

def get_wallet_balance():
    user_id = request.args.get("user_id") or request.json.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    payment_service = PaymentService(current_app.db)
    balance, error = payment_service.get_user_wallet_balance(user_id)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "Wallet balance retrieved successfully", {
        "walletBalance": balance
    })


def transfer_to_service():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")

    if not user_id or amount is None:
        return response_with_code(400, "Missing user_id or amount")

    payment_service = PaymentService(current_app.db)
    result, error = payment_service.transfer_wallet_to_service(user_id, amount)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "Amount transferred to service", result)


def transfer_to_course():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")

    if not user_id or amount is None:
        return response_with_code(400, "Missing user_id or amount")

    payment_service = PaymentService(current_app.db)
    result, error = payment_service.transfer_wallet_to_course(user_id, amount)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "Amount transferred to course", result)

def request_wallet_addition():
    data = request.get_json()
    user_id = data.get("user_id")
    upi = data.get("walletUpi")
    upi_mobile = data.get("walletUpiMobileNumber")
    amount = data.get("amount")

    if not user_id or not upi or not upi_mobile or not amount:
        return response_with_code(400, "Missing required fields")

    payment_service =PaymentService(current_app.db)
    success, message = payment_service.request_money_addition(user_id, upi, upi_mobile, amount)

    if not success:
        return response_with_code(400, message)

    return response_with_code(200, "Request to add money submitted", {"requestedAmount": amount})


def approve_wallet_addition():
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return response_with_code(400, "Missing user_id")

    payment_service =PaymentService(current_app.db)
    success, message = payment_service.approve_wallet_addition(user_id)

    if not success:
        return response_with_code(400, message)

    return response_with_code(200, "Wallet balance updated successfully")

def course_to_service_transfer():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")

    if not user_id or not amount:
        return response_with_code(400, "Missing user_id or amount")

    service = PaymentService(current_app.db)
    result, error = service.transfer_course_to_service(user_id, int(amount))

    if error:
        return response_with_code(400, error)

    return response_with_code(200, f"Transferred ₹{amount} from Course to Service", result)
