

from datetime import datetime, timedelta
from bson import ObjectId
import calendar
from app.utils import send_emi_confirmation_email

class Payment:
    def __init__(self, db):
        self.payment = db.payment

    def create_payment(self, user_id, plan_amount, upi, upi_mobile_number,plan_type):
        now = datetime.utcnow()
        user_referral_id = f"US{str(ObjectId(user_id))[-6:].upper()}S"

        upi_history_entry = {
            "upi": upi,
            "upiMobileNumber": upi_mobile_number,
            "timestamp": now
        }
        if plan_type == "C":
            service_balance = 0
            course_balance = 0
        else:
            service_balance = 0
            course_balance = 0

        collaborator_commission = 0

        wallet_balance = service_balance + course_balance

        return self.payment.insert_one({
            "userId": ObjectId(user_id),
            "userReferredId": user_referral_id,  
            "registrationAmount": 5000,
            "collaboratorCommission": collaborator_commission,
            "initialPlanType": plan_type,
            "createdAt": now,
            "updatedAt": now,
            "upi": upi,
            "upiMobileNumber": upi_mobile_number,
            "upiHistory": [upi_history_entry],
            "registrationPaymentPaid":False,
            "initialPlanAorBaccepted":False,
            "collaboratorWallet": {
                "addMoneyRequest": False,
                "courseToServiceTransfer": False,
                "walletBalance": wallet_balance,
                "serviceWalletBalance": service_balance,
                "courseWalletBalance": course_balance,
                "requestedAddMoneyToCourseWallet": 0,
                "amtTransferredToService": 0,
                "amtTransferredFromCourseToService": 0,
                "amtTransferredFromCourseToServiceHistory": [],
                "walletUpi": upi,
                "walletUpiMobileNumber": upi_mobile_number,
                "coupens": []
            },
            "plots":[],
            "additionalPlotPurchase":{
                "purcharseRequested":False,
                "plots": None,
                "initialPlanType": None,
                "sq_feet": None,
                "planAmount": None,
                "upi": None,
                "upiMobileNumber": None,
                "planAorBaccepted": False,
                "purcharseHistory":[]
            },
             "collaboratorCommission": { 
                    "collaboratorCommissionHistory": [],
                    "collaboratorCommissionWalletBalance" : 0,
                    "collaboratorCommissionRequestedWithdrawMoneyFromWallet" : 0,
                    "collaboratorCommissionWalletUpi": upi,
                    "collaboratorCommissionWithdrawRequest": False,                     
                    "collaboratorCommissionWalletUpiMobileNumber": upi_mobile_number,
                    "collaboratorWithdrawHistory": []                
            }
        })
        
    def get_payment_by_user(self, user_id):
        return self.payment.find_one({"userId": ObjectId(user_id)})

    def get_plan_type(self, user_id):
        record = self.payment.find_one({"userId": ObjectId(user_id)})
        return record.get("initialPlanType") if record else None

    def check_emi_status(self, auth_model):
        overdue_users = []
        today = datetime.utcnow()
        alert_time = today.replace(day=10, hour=12, minute=0, second=0, microsecond=0)

        # Only check for Plan C users whose EMI is pending
        users = self.payment.find({"initialPlanType": "C", "fullPaymentStatus": "Pending"})

        for u in users:
            due_date = u.get("nextDueDate")
            if due_date and today > due_date:
                update_fields = {
                    "updatedAt": today,
                    # Add next due date again for the next EMI cycle
                    "nextDueDate": due_date + timedelta(days=30),
                    "canParticipateLuckyDraw": False,
                    "luckyDrawMessage": "Not Eligible",
                }

                self.payment.update_one(
                    {"_id": u["_id"]},
                    {"$set": update_fields}
                )

                # Update user to block Lucky Charm participation
                auth_model.update(
                    {"_id": u["userId"]},
                    {"$set": {"canParticipateLuckyDraw": False}}
                )

                overdue_users.append(str(u["userId"]))

            # EMI alert logic on every 10th at 12:00 PM UTC
            elif due_date and today.date() == alert_time.date() and today.hour == 12:
                # Here you would send a notification or email alert (to be implemented)
                pass  # e.g., send_emi_alert_email(user_email)

        return overdue_users


    def update_emi_month_progress(self, user_id):
        payment = self.get_payment_by_user(user_id)
        if not payment or payment.get("initialPlanType") != "C":
            return None

        paid = payment.get("paidMonths", 1)
        if paid < 60:
            new_paid = paid + 1
            new_pending = 60 - new_paid

            update_fields = {
                "paidMonths": new_paid,
                "pendingMonths": new_pending,
                "updatedAt": datetime.utcnow()
            }

            if new_pending == 0:
                update_fields["fullPaymentStatus"] = "Completed"
                update_fields["nextDueDate"] = None
                update_fields["canParticipateLuckyDraw"] = True
                update_fields["luckyDrawMessage"] ="Eligible"

            else:
                user = self.auth_model.find_by_id(user_id)
                if user:
                    send_emi_confirmation_email(user)

            self.payment.update_one(
                {"userId": ObjectId(user_id)},
                {"$set": update_fields}
            )

            if paid > 1 and new_pending > 0:
                user = self.db.users.find_one({"_id": ObjectId(user_id)})
                if user:
                    send_emi_confirmation_email(user)

            return update_fields

        return {"message": "EMI payment already completed."}

    def update_one(self, filter_dict, update_dict):
        if "$set" in update_dict:
            update_dict["$set"]["updatedAt"] = datetime.utcnow()
        else:
            update_dict["$set"] = {"updatedAt": datetime.utcnow()}
        return self.payment.update_one(filter_dict, update_dict)

    def find_all(self):
        return list(self.payment.find())

    def find_payment_by_user_id(self, user_id):
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            payment = self.payment.find_one({'userId': user_id})
            return payment
        except Exception as e:
            print(f"❌ Payment fetch failed for user {user_id}: {e}")
            return None

    def update_wallet_fields(self, user_id, update_fields):
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        update_fields["updatedAt"] = datetime.utcnow()
        result = self.payment.update_one(
            {"userId": user_id},
            {"$set": update_fields}
        )
        return result

    def update_commission_for_collaborator(self, user_referred_id, new_user_id, commission_amount):
        collaborator = self.payment.find_one({"userReferredId": user_referred_id})
        if not collaborator:
            return True, "not a collaborator"
        
        if new_user_id in collaborator.get("collaboratorReferredList", []):
            return True, "already referred"

        commission_history_entry = {
            "userId": new_user_id,
            "commissionAmount": commission_amount,
            "timestamp": datetime.utcnow()
        }

        self.payment.update_one(
            {"userReferredId": user_referred_id},
            {
                "$addToSet": {"collaboratorReferredList": new_user_id},
                "$inc": {"collaboratorCommission.collaboratorCommissionWalletBalance": commission_amount},
                "$push": {"collaboratorCommission.collaboratorCommissionHistory": commission_history_entry}
            }
        )

        
    def approve_add_money_to_wallet(self, user_id):
        payment = self.get_payment_by_user(user_id)
        if not payment:
            return False, "Payment record not found"

        wallet = payment.get("collaboratorWallet", {})
        requested = wallet.get("requestedAddMoneyToCourseWallet", 0)
        course_balance = wallet.get("courseWalletBalance", 0)
        service_balance = wallet.get("serviceWalletBalance", 0)

        if requested <= 0:
            return False, "No amount requested"

        new_course_balance = course_balance + requested
        total_wallet_balance = new_course_balance + service_balance

        update_fields = {
            "collaboratorWallet.courseWalletBalance": new_course_balance,
            "collaboratorWallet.walletBalance": total_wallet_balance,
            "collaboratorWallet.requestedAddMoneyToCourseWallet": 0,
            "collaboratorWallet.addMoneyRequest": False
        }

        self.update_wallet_fields(user_id, update_fields)
        return True, None

    def delete_by_user_id(self, user_id):
        return self.payment.delete_one({"userId": ObjectId(user_id)})