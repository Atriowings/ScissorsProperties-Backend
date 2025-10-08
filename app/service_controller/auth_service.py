from app.model_controller.auth_model import User
from app.model_controller.payment_model import Payment
from app.model_controller.partner_model import Partner
from app.model_controller.create_plots_model import PlotModel
from app.utils import generate_username, generate_password,response_with_code,convert_objectid_to_str
from bson import ObjectId
from werkzeug.security import generate_password_hash
import random
from datetime import datetime,timedelta

class AuthService:
    def __init__(self, db): 
        self.auth_model = User(db)
        self.payment_model=Payment(db)
        self.partner_model=Partner(db)
        self.create_plots_model = PlotModel(db)

    def signup(self, data):
        existing_user = self.auth_model.find_by_email(data.email) or self.auth_model.find_by_mobile(data.mobile_number)
        if existing_user:
            user_id = existing_user["_id"]
            created_at = existing_user.get("createdAt")
            has_paid = existing_user.get("hasCompletedInitialPayment", False)

            if created_at:
                now = datetime.utcnow()
                time_diff = now - created_at

                if not has_paid:
                    if time_diff > timedelta(seconds=10):
                        # ✅ Delete stale, unpaid user data
                        self.auth_model.delete_user_by_id(user_id)
                        self.payment_model.delete_by_user_id(user_id)
                        self.create_plots_model.delete_by_user_id(user_id)
                        self.partner_model.remove_referral_user(user_id)

                        return None, "You did not complete payment within 15 minutes. Please register again."
                    else:
                        return None, "User already exists. Please complete payment."
                else:
                    return None, "User already exists and payment is completed."
            else:
                return None, "User already exists (missing createdAt)."

        # ✅ Create new user if not found
        user_id = self.auth_model.create_user(data.user_name, data.mobile_number, data.email)
        user = self.auth_model.find_by_id(user_id)
        return user, None

    def signin(self, data):
        # Try finding user by username, email, mobile, or partnerName
        user = (
            self.auth_model.find_by_username(data.login_input)
            or self.auth_model.find_by_email(data.login_input)
            or self.auth_model.find_by_mobile(data.login_input)
            or self.auth_model.find_by_partnername(data.login_input)  
        )

        if not user:
            return None, "User not found"

        if user.get("userStatus") != "Accepted":
            return None, f"Access denied. Your registration status is '{user.get('userStatus', 'Unknown')}'. Please wait for approval."

        if not user.get('password'):
            return None, "Password not set. Please contact support"

        if not self.auth_model.check_password(user['password'], data.password):
            return None, "Incorrect password"

        return str(user['_id']), None


    def user_change_password(self, user_id, data):
        if data.new_password != data.confirm_password:
            return False, "Passwords do not match"

        user = self.auth_model.find_by_id(user_id)
        if not user:
            return False, "User not found"

        if user.get("userStatus") != "Accepted":
            return False, f"Cannot change password. Status is '{user.get('userStatus')}'."

        hashed_password = generate_password_hash(data.new_password)
        result = self.auth_model.update_one(
            {"_id": ObjectId(user_id)},
            {"password": hashed_password}
        )

        if result.modified_count == 0:
            return False, "Password not updated"

        return True, None

    def update_password(self, user_id, new_password):
        user = self.auth_model.find_by_id(user_id)
        if not user:
            return False

        if user.get("userStatus") != "Accepted":
            return False

        hashed = generate_password_hash(new_password)
        result = self.auth_model.update_one({'_id': ObjectId(user_id)}, {'password': hashed})
        return result.modified_count == 1
    

    # def update_password(self, email, new_password):
    #     user = self.auth_model.find_by_email(email)

    #     if not user:
    #         return False, "User not found"

    #     if user.get("userStatus") != "Accepted":
    #         return False, f"Cannot change password. Status is '{user.get('userStatus')}'."

    #     hashed = hash_password(new_password)
    #     result = self.auth_model.update({'email': email}, {'password': hashed})

    #     if result.modified_count == 1:
    #         return True, None

    #     return False, "Update failed"


    def find_user_by_email(self, email):
        return self.auth_model.find_by_email(email)

    def generate_otp(self, length=6):
        return ''.join(str(random.randint(0, 9)) for _ in range(length))

    def store_otp(self, email, otp):
        return self.auth_model.store_otp(email, otp)

    def verify_otp(self, user, otp, expiry_minutes=15):
        if not user.get('otp') or not user.get('otp_created_at'):
            return False
        if user['otp'] != otp:
            return False
        otp_age = datetime.utcnow() - user['otp_created_at']
        if otp_age > timedelta(minutes=expiry_minutes):
            return False
        return True

    # def update_password(self, email, new_password):
    #     return self.auth_model.update_password(email, new_password)

    def find_user_by_otp(self, otp):
        return self.auth_model.find_by_otp(otp)

    def get_customer_dashboard(self, user_id):
        try:
            user = self.auth_model.find_by_id(user_id)
            if not user:
                return response_with_code(404, "User not found")

            payment = self.auth_model.find_payment_by_user_id(user_id)
            partner = self.auth_model.find_partner_by_user_id(user_id)
            plots_list = self.auth_model.find_plots_by_user_id(user_id)  # return list of plots

            user_data = {
                "_id": str(user.get('_id')),
                "user_name": user.get('user_name'),
                "mobile_number": user.get('mobile_number'),
                "email": user.get('email'),
                "userStatus": user.get('userStatus'),
                "requestType": user.get('requestType'),
                "isPartner": user.get('isPartner'),
                "userDisabled": user.get('userDisabled'),
                "createdAt": str(user.get('createdAt')),
                "updatedAt": str(user.get('updatedAt')),
                "isEmailVerified": user.get('isEmailVerified'),
                "referralId": user.get('referralId'),
                "referredBy": user.get('referredBy'),
                "credentialsSent": user.get('credentialsSent'),
                "plots": user.get('plots'),
                "username": user.get('username'),
                "partnerName": user.get('partnerName'),
                "disabled": user.get('disabled'),
                "partnerStatus": user.get('partnerStatus'),
            }

            # ✅ PAYMENT DATA (based only on create_payment fields)
            payment_data = {}
            if payment:
                wallet = payment.get("collaboratorWallet", {})
                additional = payment.get("additionalPlotPurchase", {})
                collaborator_commission = payment.get("collaboratorCommission", {})

                payment_data = {
                    "_id": str(payment.get('_id')),
                    "planType": payment.get('planType'),
                    "registrationAmount": payment.get('registrationAmount'),
                    "upi": payment.get('upi'),
                    "upiMobileNumber": payment.get('upiMobileNumber'),
                    "upiHistory": payment.get('upiHistory', []),
                    "plots": payment.get('plots', []),
                    "createdAt": str(payment.get('createdAt')),
                    "updatedAt": str(payment.get('updatedAt')),
                    "userReferredId": payment.get('userReferredId'),
                    "collaboratorWallet": {
                        "walletBalance": wallet.get("walletBalance"),
                        "serviceWalletBalance": wallet.get("serviceWalletBalance"),
                        "courseWalletBalance": wallet.get("courseWalletBalance"),
                        "requestedAddMoneyToCourseWallet": wallet.get("requestedAddMoneyToCourseWallet"),
                        "amtTransferredToService": wallet.get("amtTransferredToService"),
                        "amtTransferredFromCourseToService": wallet.get("amtTransferredFromCourseToService"),
                        "amtTransferredFromCourseToServiceHistory": wallet.get("amtTransferredFromCourseToServiceHistory"),
                        "walletUpi": wallet.get("walletUpi"),
                        "walletUpiMobileNumber": wallet.get("walletUpiMobileNumber"),
                        "coupens": wallet.get("coupens"),
                        "addMoneyRequest": wallet.get("addMoneyRequest"),
                        "courseToServiceTransfer": wallet.get("courseToServiceTransfer")
                    },
                    "collaboratorCommission": {
                        "collaboratorCommissionWalletBalance": collaborator_commission.get("collaboratorCommissionWalletBalance"),
                        "collaboratorCommissionRequestedWithdrawMoneyFromWallet": collaborator_commission.get("collaboratorCommissionRequestedWithdrawMoneyFromWallet"),
                        "collaboratorCommissionWalletUpi": collaborator_commission.get("collaboratorCommissionWalletUpi"),
                        "collaboratorCommissionWalletUpiMobileNumber": collaborator_commission.get("collaboratorCommissionWalletUpiMobileNumber"),
                        "collaboratorCommissionWithdrawRequest": collaborator_commission.get("collaboratorCommissionWithdrawRequest"),
                        "collaboratorWithdrawHistory": collaborator_commission.get("collaboratorWithdrawHistory", []),
                        "collaboratorCommissionHistory": collaborator_commission.get("collaboratorCommissionHistory", [])
                    },
                        "additionalPlotPurchase": {
                        "purcharseRequested": additional.get("purcharseRequested"),
                        "plots": additional.get("plots"),
                        "planType": additional.get("planType"),
                        "sq_feet": additional.get("sq_feet"),
                        "planAmount": additional.get("planAmount"),
                        "planAorBaccepted": additional.get("planAorBaccepted"),
                        "upi": additional.get("upi"),
                        "upiMobileNumber": additional.get("upiMobileNumber"),
                        "purcharseHistory": additional.get("purcharseHistory", [])
                    }
                }

            # ✅ PARTNER DATA
            partner_data = {}
            if partner:
                commission_wallet = partner.get("commissionWallet", {})
                partner_data = {
                    "_id": str(partner.get('_id')),
                    "partnerStatus": partner.get('partnerStatus'),
                    "myReferralId": partner.get('myReferralId'),
                    "upi": partner.get('upi'),
                    "upiMobileNumber": partner.get('upiMobileNumber'),
                    "partnerDisabled": partner.get('partnerDisabled'),
                    "upgradeType": partner.get('upgradeType'),
                    "joinedAt": str(partner.get('joinedAt')),
                    "referrals": partner.get('referrals'),
                    "commissionWallet": {
                        "commissionWalletBalance": commission_wallet.get("commissionWalletBalance"),
                        "commissionRequestedWithdrawMoneyFromWallet": commission_wallet.get("commissionRequestedWithdrawMoneyFromWallet"),
                        "commissionWalletUpi": commission_wallet.get("commissionWalletUpi"),
                        "commissionWalletUpiMobileNumber": commission_wallet.get("commissionWalletUpiMobileNumber"),
                        "commissionWithdrawRequest": commission_wallet.get("commissionWithdrawRequest"),
                        "withdrawHistory": commission_wallet.get("withdrawHistory", [])
                    }
                }

            # ✅ MULTIPLE PLOTS DATA
            plots_data = []
            if plots_list and isinstance(plots_list, list):
                for plot in plots_list:
                    plots_data.append({
                        "_id": str(plot.get('_id')),
                        "plots": plot.get('plots'),
                        "planType": plot.get('planType'),
                        "planAmount": plot.get('planAmount'),
                        "fullPaymentStatus": plot.get('fullPaymentStatus'),
                        "nextDueDate": str(plot.get('nextDueDate')) if plot.get('nextDueDate') else None,
                        "totalMonths": plot.get('totalMonths'),
                        "paidMonths": plot.get('paidMonths'),
                        "pendingMonths": plot.get('pendingMonths'),
                        "pendingMonthsList": plot.get('pendingMonthsList'),
                        "upi": plot.get('upi'),
                        "upiMobileNumber": plot.get('upiMobileNumber'),
                        "pendingAmount": plot.get('pendingAmount', 0),  # optional
                        "paidAmount": plot.get('paidAmount'),
                        "nextDue": plot.get('nextDue'),
                        "nextDueMonth": plot.get('nextDueMonth'),
                        "createdAt": str(plot.get('createdAt')),
                        "updatedAt": str(plot.get('updatedAt')),
                        "emiType": plot.get('emiType'),
                        "emiPaymentRequested": plot.get('emiPaymentRequested'),
                        "requestedEmiPaymentAmount": plot.get('requestedEmiPaymentAmount'),
                    })

            dashboard_data = {
                "user": user_data,
                "payment": payment_data,
                "partner": partner_data,
                "plots": plots_data
            }

            return response_with_code(200, "User dashboard data fetched", convert_objectid_to_str(dashboard_data))


        except Exception as e:
            return response_with_code(500, f"Server error: {str(e)}")

    def find_by_id(self, user_id):
        return self.auth_model.find_by_id(user_id)
        
    def update_user_by_id(self, user_id, update_data):
        return self.auth_model.update_user_by_id(user_id, update_data)

    def assign_partner_name(self, user_id):
        return self.auth_model.assign_partner_name(user_id)
