from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from werkzeug.security import generate_password_hash
import random
import string
import re

from app.model_controller.auth_model import User
from app.model_controller.payment_model import Payment
from app.model_controller.admin_model import Admin
from app.utils import (
    send_admin_notification_email,
    send_credentials_email,
    send_emi_confirmation_email,
    response_with_code
)

class PaymentService:
    def __init__(self, db):
        self.db = db
        self.auth_model = User(db)
        self.payment_model = Payment(db)
        self.admin_model = Admin(db)

    def complete_payment_flow(self, user_id, plan_type,upi,upi_mobile_number):
        plan_map = {
            'A': 600000,
            'B': 300000,
            'C': 5000 * 60 
        }

        total_amount = plan_map.get(plan_type)
        if not total_amount:
            return None, "Invalid plan type"

        user = self.auth_model.find_user_by_id(user_id)
        if not user:
            return None, "User not found"

        existing_payment = self.payment_model.get_payment_by_user(user_id)
        is_first_payment = existing_payment is None

        if not upi or not upi_mobile_number:
            return None, "UPI and UPI Mobile Number are required"


        # Step 1: Store ₹5000 registration payment only if first time
        if is_first_payment:
            self.payment_model.create_payment(user_id, plan_type,total_amount,upi,upi_mobile_number)

        # ✅ Don't send credentials for Plan C here — wait for admin approval
        if plan_type == 'C':
            self.send_admin_credentials_email(user, plan_type)

        elif plan_type in ['A', 'B']:
            self.send_admin_credentials_email(user, plan_type)

        return str(user_id), None


    # def complete_payment_flow(self, user_id, plan_type):
    #     plan_map = {
    #         'A': 600000,
    #         'B': 300000,
    #         'C': 5000 * 60
    #     }

    #     total_amount = plan_map.get(plan_type)
    #     if not total_amount:
    #         return None, "Invalid plan type"

    #     user = self.auth_model.find_user_by_id(user_id)
    #     if not user:
    #         return None, "User not found"

    #     existing_payment = self.payment_model.get_payment_by_user(user_id)
    #     is_first_payment = existing_payment is None

    #     # Step 1: Store ₹5000 registration payment
    #     self.payment_model.create_payment(user_id, plan_type, 5000)

    #     # ✅ Do NOT set status = Accepted yet — wait for admin approval
    #     # ❌ self.auth_model.update(...)

    #     if plan_type in ['A', 'B']:
    #         # Step 2: Notify admin after user registered
    #         self.send_admin_credentials_email(user, plan_type)

    #     elif plan_type == 'C':
    #         # Step 3: If Plan C
    #         if is_first_payment:
    #             self.generate_credentials_and_send(user_id, user)
    #         else:
    #             send_emi_confirmation_email(user)

    #     return str(user_id), None

    def send_admin_credentials_email(self, user, plan_type):
        user_data = {
            "user_name": user.get("userName") or user.get("user_name"),
            "email": user.get("email"),
            "mobile_number": user.get("mobile_number"),
            "plan": plan_type,
            "amount": 5000
        }
        send_admin_notification_email(user_data)

    def generate_credentials_and_send(self, user_id, user):
        prefix = "50055"
        suffix = "5"
        password_length = 8
        zfill_width = 2

        last_user = self.auth_model.get_last_approved_user()
        match = re.fullmatch(rf"{prefix}(\d+){suffix}", last_user.get("username", "")) if last_user else None

        if match:
            last_middle = int(match.group(1))
            new_middle = str(last_middle + 1).zfill(zfill_width)
        else:
            new_middle = "01"

        new_user_id = f"{prefix}{new_middle}{suffix}"
        plain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=password_length))
        hashed_password = generate_password_hash(plain_password)

        updated = self.auth_model.update_user_status_accepted(user_id, new_user_id, hashed_password)
        if updated:
            try:
                send_credentials_email(new_user_id, plain_password, [user['email']])
            except Exception as e:
                print(f"Failed to send email to {user['email']}: {e}")
        return updated


    # def mark_full_payment_and_send_credentials(self, user_id):
    #     user = self.auth_model.find_user_by_id(user_id)
    #     if not user:
    #         return False, "User not found"

    #     self.payment_model.mark_payment_complete(user_id)

    #     # Only send credentials now for Plan A/B
    #     self.generate_credentials_and_send(user_id, user)
    #     return True, "Full payment completed and credentials sent"
    
    
    def mark_payment_complete_and_send_credentials(self, user_id):
        user = self.auth_model.find_user_by_id(user_id)
        if not user:
            return response_with_code(404, "User not found")

        plan_type = self.get_plan_type(user_id)
        if plan_type not in ['A', 'B']:
            return response_with_code(400, "Invalid plan type for full payment")

        self.db.payment.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "fullPaymentStatus": "Completed",
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        if self.auth_model.has_sent_credentials(user_id):
            return response_with_code(200, "Payment marked as complete. Credentials already sent.")

        prefix = "500550"
        suffix = "5"
        retry_limit = 5

        last_user = self.auth_model.get_last_approved_user()
        if last_user and last_user.get("username", "").startswith(prefix):
            try:
                middle = int(last_user["username"][6:8])
            except:
                middle = 0
        else:
            middle = 0

        for _ in range(retry_limit):
            new_middle = str(middle + 1).zfill(2)
            username = f"{prefix}{new_middle}{suffix}"
            plain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            hashed_password = generate_password_hash(plain_password)

            try:
                result = self.db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {
                        "$set": {
                            "username": username,
                            "password": hashed_password,
                            "credentialsSent": True,
                            "updatedAt": datetime.utcnow()
                        }
                    }
                )
                if result.modified_count > 0:
                    send_credentials_email(username, plain_password, user['email'])
                    return response_with_code(200, "Payment complete and credentials sent")
            except DuplicateKeyError:
                middle += 1
                continue

        return response_with_code(500, "Failed to generate unique username after retries.")



    def get_plan_type(self, user_id):
        payment = self.payment_model.get_payment_by_user(user_id)
        return payment.get("planType") if payment else None


    def get_all_collaborators(self):
        users = self.auth_model.find_all()
        payments = self.payment_model.find_all()

        payment_map = {str(payment["userId"]): payment for payment in payments}

        collaborators = []
        for user in users:
            user_id = str(user["_id"])
            payment = payment_map.get(user_id)
            if payment:
                collaborators.append({
                    "userId": user_id,
                    "name": user.get("user_name", ""),
                    "email": user.get("email", ""),
                    "mobile": user.get("mobile_number", ""),
                    "userStatus": user.get("userStatus", ""),
                    "planType": payment.get("planType", ""),
                    "planAmount": payment.get("planAmount", 0),
                    "registrationAmount": payment.get("registrationAmount", 0),
                    "fullPaymentStatus": payment.get("fullPaymentStatus", ""),
                    "nextDueDate": payment.get("nextDueDate"),
                    "canParticipateLuckyDraw": payment.get("canParticipateLuckyDraw", False),
                    "luckyDrawMessage": payment.get("luckyDrawMessage", "")
                })

        return collaborators
    
    def get_user_wallet_balance(self, user_id):
        user = self.auth_model.find_user_by_id(user_id)
        if not user:
            return 0, "User not found"

        payment = self.payment_model.find_payment_by_user_id(user_id)
        if not payment:
            return 0, "Payment record not found"

        if payment.get("planType") != "C":
            return 0, None  # Wallet feature is for Plan C only

        # Monthly wallet logic
        last_updated = payment.get("updatedAt")
        if last_updated:
            now = datetime.utcnow()
            if last_updated.month != now.month or last_updated.year != now.year:
                # Reset wallet to 5000 and update timestamp
                self.payment_model.update_payment_wallet(user_id, 5000)
                return 5000, None

        return payment.get("walletBalance", 0), None
    
    def get_user_wallet_balance(self, user_id):
        user = self.auth_model.find_user_by_id(user_id)
        if not user:
            return 0, "User not found"

        payment = self.payment_model.find_payment_by_user_id(user_id)
        if not payment:
            return 0, "Payment record not found"

        if payment.get("planType") != "C":
            return 0, None

        wallet = payment.get("collaboratorWallet", {})
        last_updated = payment.get("updatedAt")
        now = datetime.utcnow()

        if last_updated and (last_updated.month != now.month or last_updated.year != now.year):
            self.payment_model.update_payment_wallet(user_id, 5000)
            return 5000, None

        return wallet.get("walletBalance", 0), None

    def transfer_wallet_to_service(self, user_id, amount):
        payment = self.payment_model.get_payment_by_user(user_id)
        if not payment:
            return None, "Payment record not found"

        if payment.get("planType") != "C":
            return None, "Wallet feature only available for Plan C"

        wallet = payment.get("collaboratorWallet", {})
        current_balance = wallet.get("walletBalance", 0)

        if amount > current_balance:
            return None, "Insufficient wallet balance"

        updated_wallet_balance = current_balance - amount
        new_amt_service = wallet.get("amtTransferredToService", 0) + amount

        update_fields = {
            "collaboratorWallet.walletBalance": updated_wallet_balance,
            "collaboratorWallet.amtTransferredToService": new_amt_service
        }

        self.payment_model.update_wallet_fields(user_id, update_fields)
        return update_fields, None


    def transfer_wallet_to_course(self, user_id, amount):
        payment = self.payment_model.get_payment_by_user(user_id)
        if not payment:
            return None, "Payment record not found"

        if payment.get("planType") != "C":
            return None, "Wallet feature only available for Plan C"

        wallet = payment.get("collaboratorWallet", {})
        current_balance = wallet.get("walletBalance", 0)

        if amount > current_balance:
            return None, "Insufficient wallet balance"

        updated_wallet_balance = current_balance - amount
        new_amt_course = wallet.get("amtTransferredToCourse", 0) + amount

        update_fields = {
            "collaboratorWallet.walletBalance": updated_wallet_balance,
            "collaboratorWallet.amtTransferredToCourse": new_amt_course
        }

        self.payment_model.update_wallet_fields(user_id, update_fields)
        return update_fields, None

    def request_money_addition(self, user_id, upi, upi_mobile_number, amount):
        payment = self.payment_model.get_payment_by_user(user_id)
        if not payment:
            return False, "Payment record not found"

        update_fields = {
            "collaboratorWallet.walletUpi": upi,
            "collaboratorWallet.walletUpiMobileNumber": upi_mobile_number,
            "collaboratorWallet.requestedAddMoneyToWallet": amount,
            "collaboratorWallet.addMoneyRequest": True
        }

        self.payment_model.update_wallet_fields(user_id, update_fields)
        return True, "Request submitted"

    def approve_wallet_addition(self, user_id):
        result, error = self.payment_model.approve_add_money_to_wallet(user_id)
        return result, error

