from datetime import datetime
from bson import ObjectId
from app.utils import generate_unique_referral_id,response_with_code

class Dealer:
    def __init__(self, db):
        self.dealers = db.dealers

    
    def _is_referral_id_unique(self, referral_id):
        return self.dealers.count_documents({"myReferralId": referral_id}) == 0

    def create_dealer(self, user_id, upi, upi_mobile_number, upgrade_type):
        existing_dealer = self.dealers.find_one({"userId": ObjectId(user_id)})
        if existing_dealer:
            return {
                "status": "exists",
                "message": "dealer already exists for this user"
            }

        referral_id = generate_unique_referral_id(self._is_referral_id_unique)
        return self.dealers.insert_one({
            "userId": ObjectId(user_id),
            "joinedAt": datetime.utcnow(),
            "dealerstatus": "Pending", 
            "myReferralId": referral_id,
            "upi": upi,
            "dealerDisabled":False,
            "upiMobileNumber": upi_mobile_number,
            "upgradeType": upgrade_type,            
            "referrals": [],
            "commissionWallet": { 
                # "commissionHistory": [],
                "commissionWalletBalance" : 0,
                "commissionWithdrawRequest": False,
                "commissionRequestedWithdrawMoneyFromWallet" : 0,
                "commissionWalletUpi": upi,                     
                "commissionWalletUpiMobileNumber": upi_mobile_number,
                "withdrawHistory": []                
            }
        })

    # ✅ Approve or decline dealer request
    def update_dealer_status(self, user_id, status):
        return self.dealers.update_one(
            {"userId": ObjectId(user_id)},
            {"$set": {"dealerstatus": status}}
        )

    def update_dealer_disabled_status(self, user_id, status: bool):
        return self.dealers.update_one(
            {"userId": ObjectId(user_id)},
            {"$set": {"dealerDisabled": status}}
        )

    def get_dealers_by_status(self, status):
        return list(self.dealers.find({"dealerstatus": status}))

    # ✅ Add referral under a dealer
    def add_referral(self, dealer_id, referred_user_id):
        return self.dealers.update_one(
            {"userId": ObjectId(dealer_id)},
            {"$addToSet": {"referrals": ObjectId(referred_user_id)}}
        )

    def update_wallet(self, dealer_id, amount, referral_id):
        return self.dealers.update_one(
            {"userId": ObjectId(dealer_id),"myReferralId":referral_id},
            {
                "$inc": {
                    "commissionWallet.commissionWalletBalance": amount 
                },
                "$push": {
                    "commissionHistory": {
                        "amount": amount,
                        "date": datetime.utcnow()
                    }
                }
            }
        )

    # ✅ Get a dealer by user ID
    def get_by_user(self, user_id):
        return self.dealers.find_one({"userId": ObjectId(user_id)})

    # ✅ Get all dealers (regardless of status)
    def get_all(self):
        return list(self.dealers.find())


    def request_withdraw_from_wallet(self, user_id, amount, upi, upi_mobile_number):
        return self.dealers.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "commissionWallet.requestedWithdrawMoneyFromWallet": amount,
                    "commissionWallet.walletUpi": upi,
                    "commissionWallet.walletUpiMobileNumber": upi_mobile_number,
                    "commissionWallet.commissionWithdrawRequest": True
                }
            }
        )


    def approve_withdraw_from_wallet(self, user_id):
        dealer = self.dealers.find_one({"userId": ObjectId(user_id)})
        if not dealer:
            return False, "dealer not found"

        wallet = dealer.get("commissionWallet", {})
        requested_amount = wallet.get("requestedWithdrawMoneyFromWallet", 0)
        current_balance = wallet.get("commissionWalletBalance", 0)

        if requested_amount <= 0:
            return False, "No withdrawal requested"

        if requested_amount > current_balance:
            return False, "Insufficient wallet balance"

        new_balance = current_balance - requested_amount

        self.dealers.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "commissionWallet.commissionWalletBalance": new_balance,
                    "commissionWallet.requestedWithdrawMoneyFromWallet": 0,
                    "commissionWallet.commissionWithdrawRequest": False
                },
                "$push": {
                    "commissionWallet.withdrawHistory": {
                        "amount": requested_amount,
                        "status": "Approved",
                        "date": datetime.utcnow()
                    }
                }
            }
        )
        return True, requested_amount

    def reset_wallet_withdrawal_request(self, user_id):
        return self.dealers.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "commissionWallet.requestedWithdrawMoneyFromWallet": 0,
                    "commissionWallet.commissionWithdrawRequest": False
                }
            }
        )


    def get_by_referral_code(self, referral_code):
        return self.dealers.find_one({"myReferralId": referral_code})