from datetime import datetime
from bson import ObjectId

class Partner:
    def __init__(self, db):
        self.partners = db.partners

    def create_partner(self, user_id, upi, upi_mobile_number, upgrade_type):
        return self.partners.insert_one({
            "userId": ObjectId(user_id),
            "joinedAt": datetime.utcnow(),
            "partnerStatus": "Pending",  # "Pending", "Approved", "Declined"
            "partnerWalletAmount": 0,
            "upi": upi,
            "partnerDisabled":False,
            "upiMobileNumber": upi_mobile_number,
            "upgradeType": upgrade_type,  # NEW FIELD
            "referrals": [],
            "commissionHistory": [],
            "partnerWallet" : {
                "walletBalance" : 0,
                "requestedWithdrawMoneyFromWallet" : 0,                
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

    # ✅ Add monthly commission to a partner's wallet
    def update_wallet(self, partner_id, amount):
        return self.partners.update_one(
            {"userId": ObjectId(partner_id)},
            {
                "$inc": {"walletAmount": amount},
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