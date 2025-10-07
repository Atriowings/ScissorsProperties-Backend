from flask import request, jsonify, current_app, send_file
from pydantic import BaseModel, EmailStr, ValidationError,constr
from flask_jwt_extended import jwt_required
from bson import ObjectId
from datetime import datetime
from app.service_controller.auth_service import AuthService
from app.service_controller.payment_service import PaymentService
from app.service_controller.plot_service import PlotService
from app.utils import(send_welcome_email,send_admin_notification_email,send_credentials_email, generate_otp, 
                      send_otp_email, response_with_code,send_collaborator_decline_email,send_collaborator_withdraw_request_email_to_admin,send_collaborator_wallet_notification_email)


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
        # Check if database is available
        if not current_app.db:
            return response_with_code(500, "Database connection not available")
            
        data = RegisterSchema(**request.get_json())
    except ValidationError as e:
        return response_with_code(400, "Validation error", e.errors())
    except Exception as e:
        print(f"❌ Error in Signup validation: {e}")
        return response_with_code(400, "Invalid request data")

    try:
        referred_by = data.referredBy.lower()
        referral_id = data.referredById

        # Ensure valid referredBy input
        valid_referrers = ["partner", "collaborator", "myself", "no one"]
        if referred_by not in valid_referrers:
            return response_with_code(400, f"Invalid referredBy value. Must be one of {valid_referrers}")

        # If referredBy is not "myself" or "no one", referralId must be provided
        if referred_by not in ["myself", "no one"] and not referral_id:
            return response_with_code(400, "Referral ID is required for selected referredBy")

        auth_service = AuthService(current_app.db)
        partner_user_id = None
        collaborator_user_id = None

        if referred_by == "partner":
            # Validate referralId from partners
            partner = current_app.db.partners.find_one({"myReferralId": referral_id})
            if not partner:
                return response_with_code(400, "Invalid referral ID for partner")
            partner_user_id = partner["userId"]

        elif referred_by == "collaborator":
            # Validate referralId from payment (userReferredId)
            collaborator = current_app.db.payment.find_one({"userReferredId": referral_id})
            if not collaborator:
                return response_with_code(400, "Invalid referral ID for collaborator")
            collaborator_user_id = collaborator["userId"]
            # Note: Plan C restriction must be enforced in the plan/payment step, not here

        # Proceed to create the user
        user, error = auth_service.signup(data)
        if error:
            return response_with_code(400, error)

        # Update user with referral metadata
        current_app.db.users.update_one(
            {"_id": ObjectId(user['_id'])},
            {"$set": {
                "isEmailVerified": True,
                "referredBy": referred_by,
                "referredById": referral_id
            }}
        )

        # Add to referrals
        if partner_user_id:
            current_app.db.partners.update_one(
                {"userId": ObjectId(partner_user_id)},
                {"$push": {"referrals": ObjectId(user['_id'])}}
            )

        if collaborator_user_id:
            current_app.db.payment.update_one(
                {"userId": ObjectId(collaborator_user_id)},
                {"$push": {"referrals": ObjectId(user['_id'])}}
            )

        # Send welcome email
        try:
            send_welcome_email(data.user_name, [data.email])
        except Exception as e:
            print(f"⚠️ Warning: Failed to send welcome email: {e}")
            # Don't fail the registration if email fails
        
        return response_with_code(200, "User registered successfully", str(user['_id']))
        
    except Exception as e:
        print(f"❌ Unexpected error in Signup: {e}")
        return response_with_code(500, "Internal server error during registration")
    
def Complete_payment():
    data = request.get_json()

    user_id = data.get('user_id')
    plan_type = data.get('initialPlanType')
    upi = data.get('upi')
    upi_mobile_number = data.get('upiMobileNumber')
    custom_amount = data.get('customAmount')  # 👈 newly added

    if not user_id:
        return response_with_code(400, "Missing user_id")

    if not plan_type:
        return response_with_code(400, "Missing initialPlanType")

    if not upi:
        return response_with_code(400, "Missing upi")

    if not upi_mobile_number:
        return response_with_code(400, "Missing upiMobileNumber")
    
    # ✅ validation for custom amount 👈 newly added
    if plan_type == "Other":
        if not custom_amount:
            return response_with_code(400, "Missing customAmount for Other plan")
        try:
            custom_amount = float(custom_amount)
            if custom_amount <= 0:
                return response_with_code(400, "Invalid customAmount")
        except ValueError:
            return response_with_code(400, "customAmount must be a number")


    payment_service = PaymentService(current_app.db)
    result, error = payment_service.complete_payment_flow(
        user_id,
        plan_type, 
        upi, 
        upi_mobile_number,
        custom_amount=custom_amount if plan_type == "Other" else None  # 👈 pass it 👈 newly added
        )

    if error:
        print(f"Error in complete_payment_flow: {error}")
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
    # success = auth_service.update_password(user['email'], data.new_password)
    success = auth_service.update_password(user["_id"], data.new_password)
    if not success:
        return response_with_code(500, "Failed to update password")

    auth_service.store_otp(user['email'], None)  # Clear OTP

    return response_with_code(200, "Password reset successfully")
    
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

def pay_emi_amount():
    data = request.get_json()
    user_id = data.get("user_id")
    plot_id = data.get("plot_id")
    amount = data.get("amount")
    upi = data.get("upi")
    upi_mobile_number = data.get("upi_mobile_number")

    if not user_id or not plot_id or not amount or not upi or not upi_mobile_number:
        return response_with_code(400, "user_id, plot_id, amount, upi, and upi_mobile_number are required")

    payment_service = PaymentService(current_app.db)
    result, error = payment_service.request_emi_payment(user_id, int(amount), upi, upi_mobile_number, plot_id)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "EMI payment received, pending admin approval", result)

# Route: /approve-plot
def approve_emi():
    data = request.get_json()
    user_id = data.get("user_id")
    plot_id = data.get("plot_id")

    if not user_id or not plot_id:
        return response_with_code(400, "user_id and plot_id are required")

    payment_service = PaymentService(current_app.db)
    result, error = payment_service.approve_emi_payment(user_id, plot_id)

    if error:
        return response_with_code(400, error)

    # After approving EMI, check if credentials need to be sent.   new addition
    user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
    if user and not user.get("credentialsSent"):
        # Only send credentials for EMI plans (C or D)
        plot = current_app.db.plots.find_one({"_id": ObjectId(plot_id)})
        # if plot and plot.get("emiType") and plot.get("paidMonths", 0) == 1:
        #     payment_service.mark_payment_complete_and_send_credentials(user_id)
        if plot and plot.get("emiType") and plot.get("paidMonths", 0) == 1:
            payment_service.send_credentials_for_emi_user(user_id, plot_id)    

    return response_with_code(200, "EMI payment approved", result)

def decline_emi():
    data = request.get_json()
    user_id = data.get("user_id")
    plot_id = data.get("plot_id")

    if not user_id or not plot_id:
        return response_with_code(400, "user_id and plot_id are required")

    payment_service = PaymentService(current_app.db)
    result, error = payment_service.decline_emi_payment(user_id, plot_id)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "EMI payment declined", result)
    
def get_lucky_charm_status():
    data = request.get_json()
    user_id = data.get("user_id")
    plot_id = data.get("plot_id")  # Required for checking per plot
    override_status = data.get("status")  # Optional override

    if not user_id or not plot_id:
        return response_with_code(400, "Missing user_id or plot_id")

    try:
        user_id_obj = ObjectId(user_id)
        plot_id_obj = ObjectId(plot_id)
    except Exception as e:
        return response_with_code(400, f"Invalid ID format: {e}")

    plot = current_app.db.plots.find_one({
        "_id": plot_id_obj,
        "userId": user_id_obj
    })

    if not plot:
        return response_with_code(404, "Plot not found for the given user")

    # Check for missing keys
    if "planType" not in plot or "fullPaymentStatus" not in plot:
        return response_with_code(400, "Required keys missing in plot data")

    plan_type = plot.get("planType")
    full_payment_status = plot.get("fullPaymentStatus")
    next_due_date = plot.get("nextDueDate")

    if override_status is not None:
        can_participate = bool(override_status)
        message = "Eligible" if can_participate else "Not eligible"
    else:
        if plan_type in ["A", "B"]:
            can_participate = True
            message = "Eligible"
        # elif plan_type == "C":
        elif plan_type in ["C", "D"]:    
            if full_payment_status == "Completed":
                can_participate = True
                message = "Eligible"
            else:
                if next_due_date:
                    today = datetime.utcnow()
                    due_date_obj = next_due_date if isinstance(next_due_date, datetime) else None
                    if due_date_obj and today.day > 10 and today > due_date_obj:
                        can_participate = False
                        message = "You missed the EMI deadline. Not eligible for Lucky Charm."
                    else:
                        can_participate = True
                        message = "Eligible"
                else:
                    return response_with_code(400, "nextDueDate is missing in plot data")
        else:
            can_participate = False
            message = "Invalid plan type"

    # Check if keys exist in DB and return error if missing
    if "canParticipateLuckyDraw" not in plot or "luckyDrawMessage" not in plot:
        return response_with_code(400, "Plot missing Lucky Draw status keys")

    # Update plot document with new values (optional if override is applied)
    current_app.db.plots.update_one(
        {"_id": plot_id_obj},
        {
            "$set": {
                "canParticipateLuckyDraw": can_participate,
                "luckyDrawMessage": message
            }
        }
    )

    return response_with_code(200, "Lucky charm status retrieved", {
        "plotId": str(plot_id_obj),
        "canParticipateLuckyDraw": can_participate,
        "luckyDrawMessage": message
    })


def request_plot():
    data = request.get_json()
    user_id = data.get("user_id")
    plot_type = data.get("plot_type")
    upi = data.get("upi")
    upi_mobile = data.get("upi_mobile_number")

    if not all([user_id, plot_type, upi, upi_mobile]):
        return response_with_code(400, "Missing required fields")

    plot_service = PlotService(current_app.db)
    plot_data = plot_service.request_plot(user_id, plot_type, upi, upi_mobile)
    return response_with_code(200, "Plot request created successfully", plot_data)

def approve_plot():
    data = request.get_json()
    plot_id = data.get("plot_id")
    
    print("📥 Incoming plot_id from frontend:", plot_id)

    if not plot_id:
        return response_with_code(400, "Missing plot_id")

    plot_service = PlotService(current_app.db)
    result, error = plot_service.approve_plot(plot_id)

    if error:
        return response_with_code(400, error)

    return response_with_code(200, "Plot approved successfully", result)


def request_collaborator_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")
    upi = data.get("upi")
    upi_mobile_number = data.get("upiMobileNumber")

    if not user_id:
        return response_with_code(400, "Missing user_id")
    if not amount:
        return response_with_code(400, "Missing amount")
    if not upi:
        return response_with_code(400, "Missing upi")
    if not upi_mobile_number:
        return response_with_code(400, "Missing upiMobileNumber")

    payment_service = PaymentService(current_app.db)
    auth_service = AuthService(current_app.db)

    success, message = payment_service.request_collaborator_wallet_withdraw(user_id, amount, upi, upi_mobile_number)
    if not success:
        return response_with_code(400, message)

    user = auth_service.find_by_id(user_id)
    if user:
        send_collaborator_withdraw_request_email_to_admin(
            collaborator_name=user.get("user_name"),
            email=user.get("email"),
            amount=amount
        )

    return response_with_code(200, message)


def approve_collaborator_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    payment_service = PaymentService(current_app.db)
    auth_service = AuthService(current_app.db)

    success, amount_or_msg = payment_service.approve_collaborator_wallet_withdraw(user_id)
    if not success:
        return response_with_code(400, amount_or_msg)

    user = auth_service.find_by_id(user_id)
    if user:
        send_collaborator_wallet_notification_email(
            to_email=user.get("email"),
            subject="Collaborator Wallet Withdrawal Approved",
            message=f"Your withdrawal request of ₹{amount_or_msg} has been approved.",
            user_name=user.get("user_name")
        )

    return response_with_code(200, f"Withdrawal of ₹{amount_or_msg} approved and mail sent")


def decline_collaborator_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    payment_service = PaymentService(current_app.db)
    auth_service = AuthService(current_app.db)

    collaborator = payment_service.get_collaborator_by_user(user_id)
    if not collaborator:
        return response_with_code(404, "Collaborator not found")

    success, message = payment_service.decline_collaborator_wallet_withdrawal(user_id)
    if not success:
        return response_with_code(400, message)

    user = auth_service.find_by_id(user_id)
    if user:
        send_collaborator_decline_email(
            collaborator_name=user.get("user_name"),
            to_email=user.get("email"),
            subject="Collaborator Wallet Withdrawal Declined",
            message=(
                "Your collaborator wallet withdrawal request has been declined by the admin.\n\n"
                "Please contact admin at scissors@gmail.com for further information."
            )
        )

    return response_with_code(200, "Withdrawal request declined and notification email sent")

