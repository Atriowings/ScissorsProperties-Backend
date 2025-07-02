from bson import ObjectId
from app.model_controller.partner_model import Partner
from app.model_controller.auth_model import User
from app.model_controller.payment_model import Payment
from app.utils import convert_objectid_to_str

class PartnerService:
    def __init__(self, db):
        self.partner_model = Partner(db)
        self.auth_model = User(db)
        self.payment_model = Payment(db)

    def make_partner(self, user_id):
        user = self.auth_model.find_user_by_id(user_id)
        if not user:
            return False, "User not found"
        self.payment_model.create_payment(user_id, "Partner", 19999)
        self.partner_model.create_partner(user_id)
        return True, "User marked as partner"

    def add_referred_user(self, partner_id, referred_user_id):
        return self.partner_model.add_referral(partner_id, referred_user_id)

    def get_partner_dashboard(self, user_id):
        partner = self.partner_model.get_by_user(user_id)
        if not partner:
            return None, "Partner not found"
        referrals = []
        for ref_id in partner.get("referrals", []):
            user = self.auth_model.find_user_by_id(ref_id)
            if user:
                referrals.append({
                    "userName": user.get("user_name"),
                    "email": user.get("email"),
                    "status": user.get("status")
                })

        return {
            "walletAmount": partner.get("walletAmount", 0),
            "referrals": referrals,
            "commissionHistory": partner.get("commissionHistory", [])
        }, None

    def add_monthly_commission(self, partner_id):
        return self.partner_model.update_wallet(partner_id, 1500)

    def list_all_partners(self):
        partners = self.partner_model.get_all()
        response = []
        for p in partners:
            commission_history = p.get("commissionHistory", [])
            response.append({
                "partnerId": str(p["userId"]),
                "walletAmount": p.get("walletAmount", 0),
                "totalCommissionEarned": p.get("walletAmount", 0),
                "pendingCommission": 0,
                "referredCollaborators": [str(uid) for uid in p.get("referrals", [])],
                "pendingMonths": 12 - len(commission_history),
                "dateOfJoining": p.get("joinedAt").strftime("%Y-%m-%d"),
                "lastPayoutDate": commission_history[-1]["date"].strftime("%Y-%m-%d") if commission_history else None
            })
        return response
            
    def get_all_partners_for_admin(self):
        partners = self.partner_model.get_all()

        result = []
        for partner in partners:
            user = self.auth_model.find_user_by_id(partner["userId"])
            if user:
                result.append({
                    "name": user.get("user_name"),
                    "userid": str(user.get("_id")),
                    "email": user.get("email"),
                    "mobile": user.get("mobileNumber", ""),
                    "dateOfJoining": user.get("createdAt", ""),
                    "address": user.get("address", ""),
                    "status": user.get("status", ""),
                    "partnerId": str(partner.get("_id")),
                    "referralCode": partner.get("referralCode", ""),
                    "referredCollaborators": partner.get("referrals", []),
                    "totalCommissionEarned": sum([c.get("amount", 0) for c in partner.get("commissionHistory", [])]),
                    "pendingCommission": 0,  # Optional: You can calculate based on unpaid commissions if needed
                    "lastPayoutDate": partner.get("commissionHistory", [{}])[-1].get("date", "") if partner.get("commissionHistory") else "",
                    "upgradeDate": partner.get("joinedAt", "")
                })

        return convert_objectid_to_str(result)


    def update_partner_status(self, user_id, status):
            return self.partner_model.update_partner_status(user_id, status)