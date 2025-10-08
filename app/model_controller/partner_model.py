from datetime import datetime
from bson import ObjectId
from app.utils import generate_unique_referral_id,response_with_code

class Partner:
    def __init__(self, db):
        self.partners = db.partners

    
    def _is_referral_id_unique(self, referral_id):
        return self.partners.count_documents({"myReferralId": referral_id}) == 0

    def create_partner(self, user_id, upi, upi_mobile_number, upgrade_type):
        existing_partner = self.partners.find_one({"userId": ObjectId(user_id)})
        if existing_partner:
            return {
                "status": "exists",
                "message": "Partner already exists for this user"
            }

        referral_id = generate_unique_referral_id(self._is_referral_id_unique)
        return self.partners.insert_one({
            "userId": ObjectId(user_id),
            "joinedAt": datetime.utcnow(),
            "partnerStatus": "Pending", 
            "myReferralId": referral_id,
            "upi": upi,
            "partnerDisabled":False,
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

    # ✅ Approve or decline partner request
    def update_partner_status(self, user_id, status):
        return self.partners.update_one(
            {"userId": ObjectId(user_id)},
            {"$set": {"partnerStatus": status}}
        )

    def update_partner_disabled_status(self, user_id, status: bool):
        return self.partners.update_one(
            {"userId": ObjectId(user_id)},
            {"$set": {"partnerDisabled": status}}
        )

    def get_partners_by_status(self, status):
        return list(self.partners.find({"partnerStatus": status}))

    # ✅ Add referral under a partner
    def add_referral(self, partner_id, referred_user_id):
        return self.partners.update_one(
            {"userId": ObjectId(partner_id)},
            {"$addToSet": {"referrals": ObjectId(referred_user_id)}}
        )

    def update_wallet(self, partner_id, amount, referral_id):
        return self.partners.update_one(
            {"userId": ObjectId(partner_id),"myReferralId":referral_id},
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

    # ✅ Get a partner by user ID
    def get_by_user(self, user_id):
        return self.partners.find_one({"userId": ObjectId(user_id)})

    # ✅ Get all partners (regardless of status)
    def get_all(self):
        return list(self.partners.find())


    def request_withdraw_from_wallet(self, user_id, amount, upi, upi_mobile_number):
        return self.partners.update_one(
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
        partner = self.partners.find_one({"userId": ObjectId(user_id)})
        if not partner:
            return False, "Partner not found"

        wallet = partner.get("commissionWallet", {})
        requested_amount = wallet.get("requestedWithdrawMoneyFromWallet", 0)
        current_balance = wallet.get("commissionWalletBalance", 0)

        if requested_amount <= 0:
            return False, "No withdrawal requested"

        if requested_amount > current_balance:
            return False, "Insufficient wallet balance"

        new_balance = current_balance - requested_amount

        self.partners.update_one(
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
        return self.partners.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "commissionWallet.requestedWithdrawMoneyFromWallet": 0,
                    "commissionWallet.commissionWithdrawRequest": False
                }
            }
        )


    def get_by_referral_code(self, referral_code):
        return self.partners.find_one({"myReferralId": referral_code})