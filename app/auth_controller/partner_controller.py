from flask import request, jsonify, current_app
from app.service_controller.partner_service import PartnerService
from app.service_controller.auth_service import AuthService
from app.model_controller.auth_model import User
from app.utils import response_with_code,send_wallet_withdraw_request_email_to_admin,send_partner_decline_email,send_partner_credentials_email,send_admin_notification_email,send_partner_request_email_to_admin,send_wallet_notification_email


def handle_partner_request():
    data = request.get_json()
    user_id = data.get("user_id")
    upi = data.get("upi")
    upi_mobile_number = data.get("upiMobileNumber")
    upgrade_type = data.get("upgradeType") 

    if not user_id or not upi or not upi_mobile_number or not upgrade_type:
        return response_with_code(400, "Missing user_id, UPI details, or upgradeType")

    partner_service = PartnerService(current_app.db)
    auth_service = AuthService(current_app.db)

    user = auth_service.find_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    result = partner_service.create_partner(user_id, upi, upi_mobile_number, upgrade_type)
    
    if isinstance(result, dict) and result.get("status") == "exists":
        return response_with_code(400, result["message"])

    auth_service.update_user_by_id(user_id, {
        "requestType": "Partner"
    })
    send_partner_request_email_to_admin(
        partner_name=user.get("user_name", "Unknown"),
        email=user.get("email"),
        user_id=user_id 
    )

    return response_with_code(200, "Partner request submitted successfully. Awaiting admin approval.")

def approve_partner_request():
    user_id = request.args.get("userId")
    if not user_id:
        return response_with_code(400, "Missing userId")

    auth_service = AuthService(current_app.db)
    partner_service = PartnerService(current_app.db)

    user = auth_service.find_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    # Generate and assign partnerName
    partner_name = auth_service.assign_partner_name(user_id)

    # Update user status
    auth_service.update_user_by_id(user_id, {
        # "requestType": "Partner",
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

    auth_service = AuthService(current_app.db)
    partner_service = PartnerService(current_app.db)

    user = auth_service.find_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    auth_service.update_user_by_id(user_id, {
        "requestType": "User",
        "partnerName": None,
        "paymentStatus": "Declined",
        "isPartner": False,
        "disabled": False
    })
    partner_service.update_partner_status(user_id, "Declined")

    send_partner_decline_email(user.get("user_name", "User"), user.get("email"))

    return response_with_code(200, "Partner request declined. User reverted.")

def partner_dashboard():
    user_id = request.args.get("userId")
    if not user_id:
        return response_with_code(400, "Missing userId")

    partner_service = PartnerService(current_app.db)
    data, error = partner_service.get_partner_dashboard(user_id)
    if error:
        return response_with_code(400, error)
    return response_with_code(200, "Dashboard data fetched",data )

def request_partner_wallet_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")
    upi = data.get("upi")
    upi_mobile_number = data.get("upiMobileNumber")

    if not user_id or not amount or not upi or not upi_mobile_number:
        return response_with_code(400, "Missing required fields")

    partner_service = PartnerService(current_app.db)
    auth_service = AuthService(current_app.db)

    success, message = partner_service.request_wallet_withdraw(user_id, amount, upi, upi_mobile_number)
    if not success:
        return response_with_code(400, message)

    user = auth_service.find_by_id(user_id)
    if user:
        send_wallet_withdraw_request_email_to_admin(
            partner_name=user.get("user_name"),
            email=user.get("email"),
            amount=amount
        )

    return response_with_code(200, message)

def approve_partner_wallet_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    partner_service = PartnerService(current_app.db)
    auth_service = AuthService(current_app.db)

    success, amount_or_msg = partner_service.approve_wallet_withdraw(user_id)
    if not success:
        return response_with_code(400, amount_or_msg)

    user = auth_service.find_by_id(user_id)
    if user:
        send_wallet_notification_email(
            user_name=user.get("user_name"),
            to_email=user.get("email"),
            subject="Partner Wallet Withdrawal Approved",
            message=f"Your withdrawal request of ₹{amount_or_msg} has been approved."
        )

    return response_with_code(200, f"Withdrawal of ₹{amount_or_msg} approved and mail sent")

def decline_partner_wallet_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    partner_service = PartnerService(current_app.db)
    auth_service = AuthService(current_app.db)

    partner = partner_service.get_by_user(user_id)
    if not partner:
        return response_with_code(404, "Partner not found")

    partner_service.decline_wallet_withdrawal(user_id)

    user = auth_service.find_by_id(user_id)
    if user:
        send_wallet_notification_email(
            user_name=user.get("user_name"),
            to_email=user.get("email"),
            subject="Partner Wallet Withdrawal Declined",
            message=(
                "Your partner wallet withdrawal request has been declined by the admin.\n\n"
                "Please contact admin at scissors@gmail.com for further information."
            )
        )

    return response_with_code(200, "Withdrawal request declined and notification email sent")