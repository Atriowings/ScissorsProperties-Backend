from datetime import datetime, timedelta
from bson import ObjectId
from werkzeug.security import generate_password_hash
import random
import string
from app.model_controller.create_plots_model import PlotModel
from app.model_controller.partner_model import Partner
from app.model_controller.auth_model import User
from app.model_controller.payment_model import Payment
from app.model_controller.admin_model import Admin
from app.utils import (
    send_admin_notification_email,
    send_credentials_email,
    send_emi_confirmation_email,response_with_code,
    send_emi_approved_email,send_emi_declined_email
)

class PaymentService:
    def __init__(self, db):
        self.db=db
        self.auth_model = User(db)
        self.payment_model = Payment(db)
        self.admin_model = Admin(db)
        self.partner_model=Partner(db)    
        self.create_plots_model = PlotModel(db)


    def complete_payment_flow(self, user_id, plan_type, upi, upi_mobile_number, custom_amount=None):  # 👈 newly adding custom amount
        plan_map = {
            'A': 600000,
            'B': 300000,
            'C': 5000 * 60,  # Assuming 60 months EMI
            'D': 2000 * 150 # 👈 newly adding Plan D and custom amount
        }

        # Handle "Other Amount added new"
        if plan_type == "Other":
            if not custom_amount:
               return None, "Custom amount required for Other plan"
            try:
                total_amount = float(custom_amount)
                if total_amount <= 0:
                    return None, "Custom amount must be greater than 0"
            except ValueError:
                return None, "Invalid custom amount"
        else:
            total_amount = plan_map.get(plan_type)
            if not total_amount:
               return None, "Invalid plan type"

        # this commented code place above else
        # total_amount = plan_map.get(plan_type)
        # if not total_amount:
            # return None, "Invalid plan type"

        user = self.auth_model.find_by_id(user_id)
        if not user:
            return None, "User not found"

        # Enforce collaborator restriction
        if user.get("referredBy") == "collaborator" and plan_type not in ["C", "D"]:  # != removed this bfr "C" and added not in
            return None, "Collaborator referrals are only allowed to choose Plan C or D"

        existing_payment = self.payment_model.get_payment_by_user(user_id)
        is_first_payment = existing_payment is None

        if not upi or not upi_mobile_number:
            return None, "UPI and UPI Mobile Number are required"

        if is_first_payment:
            self.payment_model.create_payment(user_id, total_amount, upi,upi_mobile_number,plan_type,custom_amount=custom_amount if plan_type == "Other" else None) # custom_amount adding newly

            self.payment_model.payment.update_one(
                {"userId": ObjectId(user_id)},
                {"$set": {"registrationPaymentPaid": True}}
            )
            self.auth_model.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"hasCompletedInitialPayment": True}}
            )

            # ADD THIS BLOCK:
        if plan_type in ['C', 'D']:
            plot_input = {
               "userId": ObjectId(user_id),
               "planType": plan_type,
               "upi": upi,
               "upiMobileNumber": upi_mobile_number
        }
        plot_data = self.create_plots_model.create_plot(plot_input)
        if plot_data:
            self.db.plots.insert_one(plot_data)
            self.create_plots_model.update_user_plots(user_id, plot_data["plots"])
        # ✅ Plan C: request EMI approval
        # if plan_type == 'C':
        if plan_type in ['C', 'D']: # plan D adding
            self.payment_model.payment.update_one(
                {"userId": ObjectId(user_id)},
                {"$set": {"emiPaymentRequested": True}}
            )
            self.send_admin_credentials_email(user, plan_type,upi)

        elif plan_type in ['A', 'B', 'Other']: # adding Other
            self.send_admin_credentials_email(user, plan_type,upi)

        return str(user_id), None
    
    def send_admin_credentials_email(self, user, plan_type,upi):
        user_data = {
            "user_name": user.get("userName") or user.get("user_name"),
            "email": user.get("email"),
            "mobile_number": user.get("mobile_number"),
            "plan": plan_type,
            "upi": upi,
            "amount": 5000
        }
        send_admin_notification_email(user_data)

    def mark_payment_complete_and_send_credentials(self, user_id):
        
        # commented from here
        user = self.auth_model.find_by_id(user_id)
        if not user:
            return response_with_code(404, "User not found")

        payment = self.payment_model.get_payment_by_user(user_id)
        if not payment:
            return response_with_code(400, "Payment record not found")

        plan_type = payment.get("initialPlanType")
        if plan_type not in ['A', 'B']:
            return response_with_code(400, "Invalid plan type for full payment")

        self.db.payment.update_one(
            {"userId": ObjectId(user_id)},
            {"$set": {"updatedAt": datetime.utcnow(),"initialPlanAorBaccepted":True}}
        ) 

        self.db.plots.update_one(
            {"userId": ObjectId(user_id)},
            {"$set": {
                "fullPaymentStatus": "Completed",
                "updatedAt": datetime.utcnow()
            }}
        )


        if self.auth_model.has_sent_credentials(user_id):
            return response_with_code(200, "Payment marked complete. Credentials already sent.")



        # ✅ Create plot data today commented from here
        plot_input = {
            "userId": ObjectId(user_id),
            "planType": plan_type,
            "upi": payment.get("upi"),
            "upiMobileNumber": payment.get("upiMobileNumber")
        }

        plot_data = self.create_plots_model.create_plot(plot_input)
        if not plot_data:
            return response_with_code(500, "Failed to create plot")
        plot_data["fullPaymentStatus"] = "Completed" 
        self.db.plots.insert_one(plot_data)
        self.create_plots_model.update_user_plots(user_id, plot_data["plots"])

        existing_plot = self.db.plots.find_one({"userId": ObjectId(user_id)})
        if existing_plot:
            self.db.plots.update_one(
                {"_id": existing_plot["_id"]},
                {
                    "$set": {
                        "additionalPlotPurchase": plot_data.get("additionalPlotPurchase", {}),
                        "updatedAt": datetime.utcnow(),
                        "fullPaymentStatus": "Completed"
                    }
                }
            )
            self.create_plots_model.update_user_plots(user_id, existing_plot["plots"])
        # else:
            # Insert new plot if not exists


        referral_id = user.get("referredById")
        if referral_id: 
            partner = self.partner_model.get_by_referral_code(referral_id)
            if partner:
                partner_id = partner.get("userId")

                plan_amount = (
                    plot_data.get("planAmount") or
                    (plot_data.get("additionalPlotPurchase") or {}).get("planAmount") or
                    0
                )
                commission = round(plan_amount * 0.10)
                self.partner_model.update_wallet(partner_id, commission, referral_id)

        user = self.auth_model.find_by_id(user_id)
        if not user:
          return response_with_code(404, "User not found")

        if self.auth_model.has_sent_credentials(user_id):
          return response_with_code(200, "Credentials already sent.")

        plot = self.db.plots.find_one({"_id": ObjectId(plot_id), "userId": ObjectId(user_id)})
        if not plot:
          return response_with_code(404, "Plot not found")        
        # ✅ Generate credentials
        prefix = "500550"
        suffix = "5"
        middle = 0
        last_user = self.auth_model.get_last_approved_user()
        if last_user and last_user.get("username", "").startswith(prefix):
            try:
                middle = int(last_user["username"][6:8])
            except:
                pass

        for _ in range(5):
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
                            "plots": plot_data["plots"],
                            "updatedAt": datetime.utcnow()
                        }
                    }
                )
                if result.modified_count > 0:
                    send_credentials_email(username, plain_password, user['email'])
                    return response_with_code(200, "Payment complete and credentials sent")
            except:
                middle += 1
                continue

        return response_with_code(500, "Failed to generate unique username.")
    # ----------

    def get_user_wallet_balance(self, user_id):
        user = self.auth_model.find_by_id(user_id)
        if not user:
            return 0, "User not found"

        payment = self.payment_model.find_payment_by_user_id(user_id)
        if not payment:
            return 0, "Payment record not found"

        wallet = payment.get("collaboratorWallet", {})
        last_updated = payment.get("updatedAt")
        now = datetime.utcnow()

        course_balance = wallet.get("courseWalletBalance", 0)
        service_balance = wallet.get("serviceWalletBalance", 0)

        # ✅ Get current total active plot count and sum of paid amounts
        user_plots = list(self.create_plots_model.plots.find({
            # "userId": ObjectId(user_id),
            # "planType": "C",
            # "plotStatus": "Approved"
            "userId": ObjectId(user_id),
            "planType": {"$in": ["C", "D"]},
            "plotStatus": "Approved"
        }))
        #
     

        current_plot_count = len(user_plots)
        current_paid_sum = sum(plot.get("paidAmount", 0) for plot in user_plots)

        # ✅ Track last credited paid sum in wallet
        last_credited_sum = wallet.get("lastCreditedPaidAmount", 0)

        # ✅ Only credit the difference (new amount)
        if current_paid_sum > last_credited_sum:
            delta = current_paid_sum - last_credited_sum
            new_course_balance = course_balance + delta
            wallet_balance = new_course_balance + service_balance

            update_fields = {
                "collaboratorWallet.courseWalletBalance": new_course_balance,
                "collaboratorWallet.walletBalance": wallet_balance,
                "collaboratorWallet.lastCreditedPaidAmount": current_paid_sum  # 💡 new tracking field
            }

            self.payment_model.update_wallet_fields(user_id, update_fields)
            return wallet_balance, None

        # Already credited same amount
        return course_balance + service_balance, None

    def transfer_course_to_service(self, user_id, amount):
        payment = self.payment_model.get_payment_by_user(user_id)
        if not payment:
            return None, "Payment record not found"

        wallet = payment.get("collaboratorWallet", {})
        course_balance = wallet.get("courseWalletBalance", 0)
        service_balance = wallet.get("serviceWalletBalance", 0)
        transferred_so_far = wallet.get("amtTransferredFromCourseToService", 0)
        history = wallet.get("amtTransferredFromCourseToServiceHistory", [])

        if course_balance < amount:
            return None, "Insufficient course wallet balance"

        if service_balance + amount > 5000:
            return None, "Service wallet limit is ₹5000"

        # Add transfer to history
        history.append({
            "amount": amount,
            "transferredAt": datetime.utcnow()
        })

        update_fields = {
            "collaboratorWallet.courseWalletBalance": course_balance - amount,
            "collaboratorWallet.serviceWalletBalance": service_balance + amount,
            "collaboratorWallet.walletBalance": (course_balance - amount) + (service_balance + amount),
            "collaboratorWallet.courseToServiceTransfer": True,
            "collaboratorWallet.amtTransferredFromCourseToService": transferred_so_far + amount,
            "collaboratorWallet.amtTransferredFromCourseToServiceHistory": history
        }

        self.payment_model.update_wallet_fields(user_id, update_fields)

        return {
            "courseWalletBalance": course_balance - amount,
            "serviceWalletBalance": service_balance + amount,
            "totalTransferred": transferred_so_far + amount,
            "history": history
        }, None
                
    def request_emi_payment(self, user_id, amount, upi, upi_mobile_number, plot_id):
        # if amount % 5000 != 0:
        #     return None, "Amount must be multiple of 5000"  new code written use it for later

        plot = self.db.plots.find_one({"_id": ObjectId(plot_id), "userId": ObjectId(user_id)})
        plan_type = plot.get("planType")
        if plan_type not in ["C", "D"]:
            return None, "Only Plan C & D support EMI payments"

        emi_size = plot.get("emiSize", 5000)  # default fallback for old data

        if amount % emi_size != 0:
            return None, f"Amount must be multiple of {emi_size}"
        # if not plot:
        #     return None, "Plot not found" #new code written use it for later
        
        # new line added and plantype old ine commented
        # if plan_type in ['C', 'D']:
        #     self.payment_model.payment.update_one(... {"emiPaymentRequested": True})

        # if plot.get("planType") not in ["C", "D"]:
        #    return None, "Only Plan C and D support EMI payments" 
           
        # if plot.get("planType") != "C":
        #     return None, "Only Plan C supports EMI payments"

        if plot.get("emiPaymentRequested", False):
            return None, "Previous EMI request is pending admin approval"

        self.db.plots.update_one(
            {"_id": ObjectId(plot_id)},
            {
                "$set": {
                    "emiPaymentRequested": True,
                    "upi": upi,
                    "upiMobileNumber": upi_mobile_number,
                    "requestedEmiPaymentAmount": amount,
                    "requestedAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        return {"message": "EMI request submitted for admin approval"}, None

    # ✅ NEW: approve EMI for specific plot
    def approve_emi_payment(self, user_id, plot_id):
        plot = self.db.plots.find_one({"_id": ObjectId(plot_id), "userId": ObjectId(user_id)})
        if not plot:
            return None, "Plot not found"

        # if plot.get("planType") != "C" or not plot.get("emiPaymentRequested", False):
        #     return None, "No pending EMI approval for this plot"
        if plot.get("planType") not in ["C", "D"] or not plot.get("emiPaymentRequested", False):
            return None, "No pending EMI approval for this plot"

        amount = plot.get("requestedEmiPaymentAmount")
        upi = plot.get("upi")
        upi_mobile_number = plot.get("upiMobileNumber")

        return self._process_single_emi(user_id, amount, upi, upi_mobile_number, plot_id)

    # ✅ NEW: process EMI per plot
    def _process_single_emi(self, user_id, amount, upi, upi_mobile_number, plot_id):
        # if amount % 5000 != 0:
        #     return None, "Amount must be multiple of 5000"

        # plot = self.db.plots.find_one({"_id": ObjectId(plot_id), "userId": ObjectId(user_id)})
        # if not plot:
        #     return None, "Plot not found"

        # paid_months = plot.get("paidMonths", 0)
        # pending_months = plot.get("pendingMonths", 60 - paid_months)
        # total_months = plot.get("totalMonths", 60)

        # remaining_months = min(amount // 5000, pending_months)

        # updated_paid = paid_months + remaining_months
        # updated_pending = total_months - updated_paid

        # pending_months_list = plot.get("pendingMonthsList", [])
        # paid_months_names = pending_months_list[:remaining_months]
        # updated_pending_list = pending_months_list[remaining_months:]

        # now = datetime.utcnow()
        # next_due_date = now + timedelta(days=30) if updated_pending > 0 else None

        # updated_paid_amount = updated_paid * 5000
        # updated_pending_amount = updated_pending * 5000

        # update_fields = {
        #     "paidMonths": updated_paid,
        #     "pendingMonths": updated_pending,
        #     "pendingMonthsList": updated_pending_list,
        #     "updatedAt": now,
        #     "paidAmount": updated_paid_amount,
        #     "pendingAmount": updated_pending_amount,
        #     "nextDueDate": next_due_date,
        #     "nextDueMonth": updated_pending_list[0] if updated_pending_list else None,
        #     "upi": upi,
        #     "upiMobileNumber": upi_mobile_number,
        #     "emiPaymentRequested": False,
        #     "requestedEmiPaymentAmount": 0,
        #     "requestedAt": None
        # }

        # if updated_paid == total_months:
        #     update_fields["fullPaymentStatus"] = "Completed"
        #     update_fields["nextDueDate"] = None
        #     update_fields["nextDueMonth"] = None
        #     update_fields["canParticipateLuckyDraw"] = True
        #     update_fields["luckyDrawMessage"] = "Eligible"
        # else:
        #     if now.day > 10:
        #         update_fields["canParticipateLuckyDraw"] = False
        #         update_fields["luckyDrawMessage"] = "You missed the EMI payment. Not eligible."

        # upi_entry = {
        #     "upi": upi,
        #     "upiMobileNumber": upi_mobile_number,
        #     "timestamp": now
        # }

        # self.db.plots.update_one(
        #     {"_id": ObjectId(plot_id)},
        #     {
        #         "$set": update_fields,
        #         "$push": {"upiHistory": upi_entry}
        #     }
        # )

        plot = self.db.plots.find_one({"_id": ObjectId(plot_id), "userId": ObjectId(user_id)})
        if not plot:
           return None, "Plot not found"

        plan_type = plot.get("planType")
        if plan_type not in ["C", "D"]:
           return None, "Only Plan C & D support EMI payments"

        emi_size = plot.get("emiSize")
        total_months = plot.get("totalMonths")

        if not emi_size or not total_months:
           return None, "Invalid EMI configuration"

        if amount % emi_size != 0:
           return None, f"Amount must be multiple of {emi_size}"

        paid_months = plot.get("paidMonths", 0)
        pending_months = plot.get("pendingMonths", total_months - paid_months)

        remaining_months = min(amount // emi_size, pending_months)

        updated_paid = paid_months + remaining_months
        updated_pending = total_months - updated_paid

        pending_months_list = plot.get("pendingMonthsList", [])
        updated_pending_list = pending_months_list[remaining_months:]

        now = datetime.utcnow()
        next_due_date = now + timedelta(days=30) if updated_pending > 0 else None

        updated_paid_amount = updated_paid * emi_size
        updated_pending_amount = updated_pending * emi_size

        update_fields = {
           "paidMonths": updated_paid,
           "pendingMonths": updated_pending,
           "pendingMonthsList": updated_pending_list,
           "updatedAt": now,
           "paidAmount": updated_paid_amount,
           "pendingAmount": updated_pending_amount,
           "nextDueDate": next_due_date,
           "nextDueMonth": updated_pending_list[0] if updated_pending_list else None,
           "upi": upi,
           "upiMobileNumber": upi_mobile_number,
           "emiPaymentRequested": False,
           "requestedEmiPaymentAmount": 0,
           "requestedAt": None
        }

        if updated_paid == total_months:
           update_fields["fullPaymentStatus"] = "Completed"
           update_fields["nextDueDate"] = None
           update_fields["nextDueMonth"] = None
           update_fields["canParticipateLuckyDraw"] = True
           update_fields["luckyDrawMessage"] = "Eligible"
        else:
            if now.day > 10:
               update_fields["canParticipateLuckyDraw"] = False
               update_fields["luckyDrawMessage"] = "You missed the EMI payment. Not eligible."

        upi_entry = {
            "upi": upi,
            "upiMobileNumber": upi_mobile_number,
            "timestamp": now
        }

        self.db.plots.update_one(
           {"_id": ObjectId(plot_id)},
           {
            "$set": update_fields,
            "$push": {"upiHistory": upi_entry}
        }
    )

        # user = self.auth_model.find_by_id(user_id)
        # ✅ Referral Commission Logic (₹1500 per month)
        user = self.auth_model.find_by_id(user_id)
        referral_id = user.get("referredById")

        if referral_id and remaining_months > 0:
            partner = self.partner_model.get_by_referral_code(referral_id)
            if partner:
                partner_id = partner.get("userId")
                commission_amount = 1500 * remaining_months
                self.partner_model.update_wallet(partner_id, commission_amount, referral_id)


        # Inside _process_single_emi, after you get user and referral info

        user = self.auth_model.find_by_id(user_id)
        referral_id = user.get("referredById")
        referred_by = user.get("referredBy")

        # Collaborator commission logic (ONLY for Plan C & userReferredId exists)
        if referred_by == "collaborator" and referral_id:
            commission_amount = 500 * remaining_months
            self.payment_model.update_commission_for_collaborator(referral_id, str(user_id), commission_amount)


        if user and updated_pending > 0:
            send_emi_confirmation_email(user, amount)

        if user:
            send_emi_approved_email(
                to_email=user.get("email"),
                user_name=user.get("user_name") or user.get("userName", "User"),
                plot_code=plot.get("plots"),
                amount=amount
            )

        return {
            "paidMonths": updated_paid,
            "pendingMonths": updated_pending,
            "pendingAmount": updated_pending_amount,
            "nextDueDate": next_due_date,
            "upi": upi,
            "upiMobileNumber": upi_mobile_number
        }, None

    def decline_emi_payment(self, user_id, plot_id):
        plot = self.db.plots.find_one({"_id": ObjectId(plot_id), "userId": ObjectId(user_id)})
        if not plot:
            return None, "Plot not found"

        if not plot.get("emiPaymentRequested", False):
            return None, "No EMI payment pending approval"

        # Reset fields
        self.db.plots.update_one(
            {"_id": ObjectId(plot_id)},
            {
                "$set": {
                    "emiPaymentRequested": False,
                    "requestedEmiPaymentAmount": 0,
                    "requestedAt": None
                }
            }
        )

        # Send email to user
        user = self.auth_model.find_by_id(user_id)
        if user:
            send_emi_declined_email(
            to_email=user.get("email"),
            user_name=user.get("user_name") or user.get("userName", "User"),
            plot_code=plot.get("plots") 
        )

        return {"message": "EMI request declined"}, None
    
    

    def request_collaborator_wallet_withdraw(self, user_id, amount, upi, upi_mobile_number):
        if amount != 10000:
            return False, "Withdrawal amount must be exactly ₹10,000"

        collaborator = self.payment_model.get_payment_by_user(user_id)
        if not collaborator or not isinstance(collaborator, dict):
            return False, "Collaborator not found"

        collaborator_commission = collaborator.get("collaboratorCommission")
        if not isinstance(collaborator_commission, dict):
            return False, "Invalid collaborator commission data"

        requested_amount = collaborator_commission.get("collaboratorCommissionRequestedWithdrawMoneyFromWallet", 0)
        if requested_amount > 0:
            return False, "You already have a pending withdrawal request"

        result = self.payment_model.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "collaboratorCommission.collaboratorCommissionRequestedWithdrawMoneyFromWallet": amount,
                    "collaboratorCommission.collaboratorCommissionWalletUpi": upi,
                    "collaboratorCommission.collaboratorCommissionWalletUpiMobileNumber": upi_mobile_number,
                    "collaboratorCommission.collaboratorCommissionWithdrawRequest": True
                }
            }
        )
        if result.modified_count == 0:
            return False, "Wallet withdraw request failed"

        return True, "Request submitted"


    def approve_collaborator_wallet_withdraw(self, user_id):
        collaborator = self.payment_model.get_payment_by_user(user_id)
        if not collaborator:
            return False, "Collaborator not found"

        wallet = collaborator.get("collaboratorCommission", {})
        requested_amount = wallet.get("collaboratorCommissionRequestedWithdrawMoneyFromWallet", 0)
        current_balance = wallet.get("collaboratorCommissionWalletBalance", 0)

        if requested_amount <= 0:
            return False, "No withdrawal requested"

        if requested_amount > current_balance:
            return False, "Insufficient wallet balance"

        new_balance = current_balance - requested_amount

        self.payment_model.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "collaboratorCommission.collaboratorCommissionWalletBalance": new_balance,
                    "collaboratorCommission.collaboratorCommissionRequestedWithdrawMoneyFromWallet": 0,
                    "collaboratorCommission.collaboratorCommissionWithdrawRequest": False
                },
                "$push": {
                    "collaboratorCommission.collaboratorWithdrawHistory": {
                        "amount": requested_amount,
                        "status": "Approved",
                        "date": datetime.utcnow()
                    }
                }
            }
        )
        return True, requested_amount

    def decline_collaborator_wallet_withdrawal(self, user_id):
        result = self.payment_model.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "collaboratorCommission.collaboratorCommissionRequestedWithdrawMoneyFromWallet": 0,
                    "collaboratorCommission.collaboratorCommissionWithdrawRequest": False
                }
            }
        )
        if result.modified_count == 0:
            return False, "Decline request failed"
        return True, "Withdrawal request declined"

    def get_collaborator_by_user(self, user_id):
        return self.payment_model.get_payment_by_user(user_id)
    


