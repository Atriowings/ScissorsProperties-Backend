from datetime import datetime, timedelta
from bson import ObjectId
import calendar

class Payment:
    def __init__(self, db):
        self.payment = db.payment

    def create_payment(self, user_id, plan_type, plan_amount, upi, upi_mobile_number):
        now = datetime.utcnow()
        current_month_label = now.strftime("%B %Y")  # e.g., "July 2025"

        # Generate next due month name
        current_month_index = now.month
        next_month_index = 1 if current_month_index == 12 else current_month_index + 1
        next_month_name = calendar.month_name[next_month_index]
        current_year = now.year
        next_due_month_label = f"{next_month_name} {current_year if next_month_index != 1 else current_year + 1}"

        # Generate pendingMonthsList for 60 months
        pending_months_list = []
        for i in range(60):
            future_date = now + timedelta(days=30 * i)
            month_year = future_date.strftime("%B %Y")
            pending_months_list.append(month_year)

        # ✅ Remove the first paid month (e.g., "July 2025")
        if current_month_label in pending_months_list:
            pending_months_list.remove(current_month_label)

        if plan_type == "C":
            paid_months = 1
            pending_months = 59
            paid_amount = 5000
            pending_amount = plan_amount - paid_amount
            next_due = 0 if pending_amount == 0 else 5000
            next_due_date = now + timedelta(days=30)
            service_balance =0
            course_balance = 5000
            wallet_balance = service_balance
        else:
            paid_months = 60
            pending_months = 0
            paid_amount = plan_amount
            pending_amount = 0
            next_due = 0
            next_due_date = None
            service_balance = 0
            course_balance = 0
            wallet_balance = 0
            next_due_month_label = None
            pending_months_list = []

        wallet_balance = course_balance + service_balance

        upi_history_entry = {
            "upi": upi,
            "upiMobileNumber": upi_mobile_number,
            "timestamp": now
        }
        # Generate referralId like "US6F57BAS"
        user_referral_id = f"US{str(ObjectId(user_id))[-6:].upper()}S"

        return self.payment.insert_one({
            "userId": ObjectId(user_id),
            "userReferredId": user_referral_id,
            "planType": plan_type,
            "planCemi": False, 
            "planAmount": plan_amount,
            "registrationAmount": 5000,
            "fullPaymentStatus": "Pending",
            "nextDueDate": next_due_date,
            "createdAt": now,
            "updatedAt": now,
            "canParticipateLuckyDraw": True,
            "luckyDrawMessage": "Eligible",
            "totalMonths": 60,
            "paidMonths": paid_months,
            "pendingMonths": pending_months,
            "pendingMonthsList": pending_months_list,
            "upi": upi,
            "upiMobileNumber": upi_mobile_number,
            "pendingAmount": pending_amount,
            "paidAmount": paid_amount,
            "nextDue": next_due,
            "nextDueMonth": next_due_month_label,
            "coupenValidityStatus": False,
            "upiHistory": [upi_history_entry],
            "collaboratorWallet": {
                "addMoneyRequest": False,
                "courseToServiceTransfer": False,
                "walletBalance": wallet_balance,
                "serviceWalletBalance": service_balance,
                "courseWalletBalance": course_balance,
                "requestedAddMoneyToCourseWallet": 0,
                "amtTransferredToService": 0,
                "amtTransferredFromCourseToService":0,
                "amtTransferredFromCourseToServiceHistory": [],
                "walletUpi": upi,
                "walletUpiMobileNumber": upi_mobile_number,
                "coupens": []
            }
        })

    def get_payment_by_user(self, user_id):
        return self.payment.find_one({"userId": ObjectId(user_id)})

    def get_plan_type(self, user_id):
        record = self.payment.find_one({"userId": ObjectId(user_id)})
        return record.get("planType") if record else None

    def check_emi_status(self, auth_model):
        overdue_users = []
        today = datetime.utcnow()
        alert_time = today.replace(day=10, hour=12, minute=0, second=0, microsecond=0)

        # Only check for Plan C users whose EMI is pending
        users = self.payment.find({"planType": "C", "fullPaymentStatus": "Pending"})

        for u in users:
            due_date = u.get("nextDueDate")
            if due_date and today > due_date:
                update_fields = {
                    "updatedAt": today,
                    # Add next due date again for the next EMI cycle
                    "nextDueDate": due_date + timedelta(days=30),
                    "canParticipateLuckyDraw": False,
                    "luckyDrawMessage": "You missed the amount. You cannot participate in the Lucky Charm."
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
        if not payment or payment.get("planType") != "C":
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
        update_dict["updatedAt"] = datetime.utcnow()
        return self.payment.update_one(filter_dict, {"$set": update_dict})
    
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
