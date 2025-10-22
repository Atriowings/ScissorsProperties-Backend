from bson import ObjectId
from app.model_controller.dealer_model import Dealer
from app.model_controller.auth_model import User
from app.model_controller.payment_model import Payment
from app.model_controller.create_plots_model import PlotModel
from app.utils import convert_objectid_to_str

class DealerService:
    def __init__(self, db):
        self.dealer_model = Dealer(db)
        self.auth_model = User(db)
        self.payment_model = Payment(db)
        self.create_plots_model = PlotModel(db)

    def create_dealer(self, user_id, upi, upi_mobile_number, upgrade_type):
        return self.dealer_model.create_dealer(user_id, upi, upi_mobile_number, upgrade_type)

    def update_dealer_status(self, user_id, status):
            return self.dealer_model.update_dealer_status(user_id, status)

    def get_by_user(self, user_id):
        return self.dealer_model.get_by_user(user_id)

    def request_wallet_withdraw(self, user_id, amount, upi, upi_mobile_number):
            if amount != 10000:
                return False, "Withdrawal amount must be exactly ₹10,000"

            dealer = self.dealer_model.get_by_user(user_id)
            if not dealer:
                return False, "Dealer not found"

            requested_amount = dealer.get("commissionWallet", {}).get("requestedWithdrawMoneyFromWallet", 0)

            # Check if there's already a pending request
            if requested_amount and requested_amount > 0:
                return False, "You already have a pending withdrawal request"

            result = self.dealer_model.request_withdraw_from_wallet(user_id, amount, upi, upi_mobile_number)
            if result.modified_count == 0:
                return False, "Wallet withdraw request failed"

            return True, "Request submitted"

    def approve_wallet_withdraw(self, user_id):
        return self.dealer_model.approve_withdraw_from_wallet(user_id)

    def decline_wallet_withdrawal(self, user_id):
        return self.dealer_model.reset_wallet_withdrawal_request(user_id)

    def get_dealer_dashboard(self, user_id):
        dealer = self.dealer_model.get_by_user(user_id)
        if not dealer:
            return None, "dealer not found"

        referrals = []
        for ref_user_id in dealer.get("referrals", []):
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

        total_commission = sum(entry.get("amount", 0) for entry in dealer.get("commissionHistory", []))

        return {
            "walletAmount": dealer.get("walletAmount", 0),
            "referrals": referrals,
            "referralCount": len(referrals),
            "commissionHistory": dealer.get("commissionHistory", []),
            "totalCommissionEarned": total_commission,
            "dealerStatus": dealer.get("dealerStatus", "Unknown"),
            "upgradeType": dealer.get("upgradeType", "N/A"),
            "myReferralId": dealer.get("myReferralId"),
            "commissionWallet": {
                "commissionWalletBalance": dealer.get("commissionWallet", {}).get("commissionWalletBalance", 0),
                "requestedWithdrawMoneyFromWallet": dealer.get("commissionWallet", {}).get("commissionRequestedWithdrawMoneyFromWallet", 0),
                "walletUpi": dealer.get("commissionWallet", {}).get("commissionWalletUpi", ""),
                "walletUpiMobileNumber": dealer.get("commissionWallet", {}).get("commissionWalletUpiMobileNumber", "")
            },
            "dateOfJoining": dealer.get("joinedAt").strftime("%Y-%m-%d") if dealer.get("joinedAt") else None
        }, None