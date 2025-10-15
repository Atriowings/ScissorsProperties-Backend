from bson import ObjectId
from app.model_controller.partner_model import Partner
from app.model_controller.auth_model import User
from app.model_controller.payment_model import Payment
from app.model_controller.create_plots_model import PlotModel
from app.utils import convert_objectid_to_str

class PartnerService:
    def __init__(self, db):
        self.partner_model = Partner(db)
        self.auth_model = User(db)
        self.payment_model = Payment(db)
        self.create_plots_model = PlotModel(db)

    def create_partner(self, user_id, upi, upi_mobile_number, upgrade_type):
        return self.partner_model.create_partner(user_id, upi, upi_mobile_number, upgrade_type)

    def update_partner_status(self, user_id, status):
            return self.partner_model.update_partner_status(user_id, status)

    def get_by_user(self, user_id):
        return self.partner_model.get_by_user(user_id)

    def request_wallet_withdraw(self, user_id, amount, upi, upi_mobile_number):
            if amount != 10000:
                return False, "Withdrawal amount must be exactly ₹10,000"

            partner = self.partner_model.get_by_user(user_id)
            if not partner:
                return False, "Partner not found"

            requested_amount = partner.get("commissionWallet", {}).get("requestedWithdrawMoneyFromWallet", 0)

            # Check if there's already a pending request
            if requested_amount and requested_amount > 0:
                return False, "You already have a pending withdrawal request"

            result = self.partner_model.request_withdraw_from_wallet(user_id, amount, upi, upi_mobile_number)
            if result.modified_count == 0:
                return False, "Wallet withdraw request failed"

            return True, "Request submitted"

    def approve_wallet_withdraw(self, user_id):
        return self.partner_model.approve_withdraw_from_wallet(user_id)

    def decline_wallet_withdrawal(self, user_id):
        return self.partner_model.reset_wallet_withdrawal_request(user_id)

    def get_partner_dashboard(self, user_id):
        partner = self.partner_model.get_by_user(user_id)
        if not partner:
            return None, "Partner not found"

        referrals = []
        for ref_user_id in partner.get("referrals", []):
            user = self.auth_model.find_by_id(ref_user_id)
            payment = self.auth_model.find_payment_by_user_id(ref_user_id)
            plots_cursor = self.create_plots_model.plots.find({"userId": ObjectId(ref_user_id)})

            referral_plots = []
            for plot in plots_cursor:
                referral_plots.append({
                    "plotId": str(plot.get("_id")),
                    "planType": plot.get("planType"),
                    "paidMonths": plot.get("paidMonths", 0),
                    "pendingMonths": plot.get("pendingMonths", 0),
                    "nextDueMonth": plot.get("nextDueMonth"),
                    "nextDueDate": plot.get("nextDueDate"),
                    "emiType": plot.get("emiType"),
                    "fullPaymentStatus": plot.get("fullPaymentStatus"),
                    "plotStatus": plot.get("plotStatus")
                })

            if user:
                referrals.append({
                    "userName": user.get("user_name"),
                    "email": user.get("email"),
                    "mobileNumber": user.get("mobile_number"),
                    "initialPlanType": payment.get("initialPlanType") if payment else None,
                    "plots": referral_plots
                })

        total_commission = sum(entry.get("amount", 0) for entry in partner.get("commissionHistory", []))

        return {
            "walletAmount": partner.get("walletAmount", 0),
            "referrals": referrals,
            "referralCount": len(referrals),
            "commissionHistory": partner.get("commissionHistory", []),
            "totalCommissionEarned": total_commission,
            "partnerStatus": partner.get("partnerStatus", "Unknown"),
            "upgradeType": partner.get("upgradeType", "N/A"),
            "myReferralId": partner.get("myReferralId"),
            "commissionWallet": {
                "commissionWalletBalance": partner.get("commissionWallet", {}).get("commissionWalletBalance", 0),
                "requestedWithdrawMoneyFromWallet": partner.get("commissionWallet", {}).get("commissionRequestedWithdrawMoneyFromWallet", 0),
                "walletUpi": partner.get("commissionWallet", {}).get("commissionWalletUpi", ""),
                "walletUpiMobileNumber": partner.get("commissionWallet", {}).get("commissionWalletUpiMobileNumber", "")
            },
            "dateOfJoining": partner.get("joinedAt").strftime("%Y-%m-%d") if partner.get("joinedAt") else None
        }, None