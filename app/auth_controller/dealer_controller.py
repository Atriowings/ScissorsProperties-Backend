from flask import request, current_app
from app.service_controller.dealer_service import DealerService
from app.service_controller.auth_service import AuthService
from app.model_controller.auth_model import User
from app.utils import response_with_code,send_wallet_withdraw_request_email_to_admin,send_dealer_decline_email,send_dealer_credentials_email,send_admin_notification_email,send_dealer_request_email_to_admin,send_wallet_notification_email

def handle_dealer_request():
    data = request.get_json()
    user_id = data.get("user_id")
    dealer_details = data.get("dealerDetails")  # Assuming dealer details are passed as a dictionary
    upgrade_type = data.get("upgradeType") 

    if not user_id or not dealer_details or not upgrade_type:
        return response_with_code(400, "Missing user_id, dealer details, or upgradeType")

    dealer_service = DealerService(current_app.db)
    auth_service = AuthService(current_app.db)

    user = auth_service.find_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    result = dealer_service.create_dealer(user_id, dealer_details, upgrade_type)
    
    if isinstance(result, dict) and result.get("status") == "exists":
        return response_with_code(400, result["message"])

    auth_service.update_user_by_id(user_id, {
        "requestType": "Dealer"
    })
    send_dealer_request_email_to_admin(
        dealer_name=user.get("user_name", "Unknown"),
        email=user.get("email"),
        user_id=user_id 
    )

    return response_with_code(200, "Dealer request submitted successfully. Awaiting admin approval.")

def approve_dealer_request():
    user_id = request.args.get("userId")
    if not user_id:
        return response_with_code(400, "Missing userId")

    auth_service = AuthService(current_app.db)
    dealer_service = DealerService(current_app.db)

    user = auth_service.find_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    # Generate and assign dealerName
    dealer_name = auth_service.assign_dealer_name(user_id)

    # Update user status
    auth_service.update_user_by_id(user_id, {
        "dealerStatus": "Approved",
        "isDealer": True,
        "disabled": False
    })

    # Update dealer status
    dealer_service.update_dealer_status(user_id, "Approved")

    # Send email (dealerName only, no password)
    send_dealer_credentials_email(dealer_name, user.get("email"))

    return response_with_code(200, f"Dealer approved and credentials sent to {user.get('email')}")

def decline_dealer_request():
    data = request.get_json()
    user_id = data.get("userId")

    if not user_id:
        return response_with_code(400, "Missing userId")

    auth_service = AuthService(current_app.db)
    dealer_service = DealerService(current_app.db)

    user = auth_service.find_by_id(user_id)
    if not user:
        return response_with_code(404, "User not found")

    auth_service.update_user_by_id(user_id, {
        "requestType": "User",
        "dealerName": None,
        "isDealer": False,
        "disabled": False
    })
    dealer_service.update_dealer_status(user_id, "Declined")

    send_dealer_decline_email(user.get("user_name", "User"), user.get("email"))

    return response_with_code(200, "Dealer request declined. User reverted.")

def dealer_dashboard():
    user_id = request.args.get("userId")
    if not user_id:
        return response_with_code(400, "Missing userId")

    dealer_service = DealerService(current_app.db)
    data, error = dealer_service.get_dealer_dashboard(user_id)
    if error:
        return response_with_code(400, error)
    return response_with_code(200, "Dashboard data fetched", data)

def request_dealer_wallet_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    amount = data.get("amount")
    upi = data.get("upi")
    upi_mobile_number = data.get("upiMobileNumber")

    if not user_id or not amount or not upi or not upi_mobile_number:
        return response_with_code(400, "Missing required fields")

    dealer_service = DealerService(current_app.db)
    auth_service = AuthService(current_app.db)

    success, message = dealer_service.request_wallet_withdraw(user_id, amount, upi, upi_mobile_number)
    if not success:
        return response_with_code(400, message)

    user = auth_service.find_by_id(user_id)
    if user:
        send_wallet_withdraw_request_email_to_admin(
            dealer_name=user.get("user_name"),
            email=user.get("email"),
            amount=amount
        )

    return response_with_code(200, message)

def approve_dealer_wallet_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    dealer_service = DealerService(current_app.db)
    auth_service = AuthService(current_app.db)

    success, amount_or_msg = dealer_service.approve_wallet_withdraw(user_id)
    if not success:
        return response_with_code(400, amount_or_msg)

    user = auth_service.find_by_id(user_id)
    if user:
        send_wallet_notification_email(
            user_name=user.get("user_name"),
            to_email=user.get("email"),
            subject="Dealer Wallet Withdrawal Approved",
            message=f"Your withdrawal request of ₹{amount_or_msg} has been approved."
        )

    return response_with_code(200, f"Withdrawal of ₹{amount_or_msg} approved and mail sent")

def decline_dealer_wallet_withdrawal():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return response_with_code(400, "Missing user_id")

    dealer_service = DealerService(current_app.db)
    auth_service = AuthService(current_app.db)

    dealer = dealer_service.get_by_user(user_id)
    if not dealer:
        return response_with_code(404, "Dealer not found")

    dealer_service.decline_wallet_withdrawal(user_id)

    user = auth_service.find_by_id(user_id)
    if user:
        send_wallet_notification_email(
            user_name=user.get("user_name"),
            to_email=user.get("email"),
            subject="Dealer Wallet Withdrawal Declined",
            message=(
                "Your dealer wallet withdrawal request has been declined by the admin.\n\n"
                "Please contact admin at scissors@gmail.com for further information."
            )
        )

    return response_with_code(200, "Withdrawal request declined and notification email sent")