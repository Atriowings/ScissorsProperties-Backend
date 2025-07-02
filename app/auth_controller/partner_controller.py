from flask import request, jsonify, current_app
from app.service_controller.partner_service import PartnerService
from app.model_controller.auth_model import User
from bson import ObjectId
from app.utils import response_with_code,send_partner_decline_email,send_partner_credentials_email,send_admin_notification_email,send_partner_request_email_to_admin

def make_partner():
    data = request.get_json()
    user_id = data.get("userId")
    if not user_id:
        return response_with_code(400, "Missing userId")

    service = PartnerService(current_app.db)
    success, message = service.make_partner(user_id)
    if not success:
        return response_with_code(400, message)
    return response_with_code(200, message)

def refer_user():
    data = request.get_json()
    partner_id = data.get("partnerId")
    referred_user_id = data.get("referredUserId")
    if not partner_id or not referred_user_id:
        return response_with_code(400, "Missing partnerId or referredUserId")

    service = PartnerService(current_app.db)
    service.add_referred_user(partner_id, referred_user_id)
    return response_with_code(200, "Referral added")

def partner_dashboard():
    user_id = request.args.get("userId")
    if not user_id:
        return response_with_code(400, "Missing userId")

    service = PartnerService(current_app.db)
    data, error = service.get_partner_dashboard(user_id)
    if error:
        return response_with_code(400, error)
    return response_with_code(200, "Dashboard data fetched",data )

def handle_partner_request():
    data = request.get_json()
    user_id = data.get("user_id")
    upi = data.get("upi")
    upi_mobile_number = data.get("upiMobileNumber")
    upgrade_type = data.get("upgradeType") 
    
    if not ObjectId.is_valid(user_id):
        return response_with_code(400, "Invalid user_id format")

    if not user_id or not upi or not upi_mobile_number or not upgrade_type:
        return response_with_code(400, "Missing user_id, UPI details, or upgradeType")

    partner_service = PartnerService(current_app.db)
    auth_model = User(current_app.db)

    user = auth_model.find_user_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    # ✅ Create partner entry (with UPI and upgradeType info)
    partner_service.partner_model.create_partner(user_id, upi, upi_mobile_number, upgrade_type)

    auth_model.update_user_by_id(user_id, {
            "requestType": "Partner",
    })
    
    # ✅ Notify admin with partner details
    send_partner_request_email_to_admin(
        partner_name=user.get("user_name", "Unknown"),
        email=user.get("email"),
        user_id=user_id
    )

    return response_with_code(200, "Partner request submitted successfully. Awaiting admin approval.")


def approve_partner_request():
    data = request.get_json()
    user_id = data.get("userId")
    if not user_id:
        return response_with_code(400, "Missing userId")

    auth_model = User(current_app.db)
    partner_service = PartnerService(current_app.db)

    user = auth_model.find_user_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    # Generate and assign partnerName
    if user.get("partnerStatus") == "Approved":
        return response_with_code(400, "This user is already approved as a partner")
    
    partner_name = auth_model.assign_partner_name(user_id)

    # Update user status
    auth_model.update_user_by_id(user_id, {
        "partnerStatus": "Approved",
        "isPartner": True,
        "disabled": False
    })

    # Update partner status
    partner_service.update_partner_status(user_id, "Approved")

    # Send email (partnerName only, no password)
    send_partner_credentials_email(partner_name, user.get("email"))

    return response_with_code(200, f"Partner approved and credentials sent to {user.get('email')}")

def decline_partner_request():
    data = request.get_json()
    user_id = data.get("userId")

    if not user_id:
        return response_with_code(400, "Missing userId")

    auth_model = User(current_app.db)
    partner_model = PartnerService(current_app.db)

    user = auth_model.find_user_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    auth_model.update_one(
        {"_id": ObjectId(user_id)},
        {
            "requestType": "User",
            "partnerName": None,
            "paymentStatus": "Declined",
            "isPartner": False,
            "disabled": False
        }
    )

    partner_model.update_partner_status(user_id, "Declined")

    send_partner_decline_email(user.get("user_name", "User"), user.get("email"))

    return response_with_code(200, "Partner request declined. User reverted.")