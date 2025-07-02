import random, string
from bson import ObjectId
from datetime import datetime
from app.service_controller.service_provided_service import ServiceProvide


class CouponService:
    def __init__(self, db):
        self.db = db
        self.service_provided_model = ServiceProvide(db) 

    def _generate_code(self, length=8):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def generate_coupon(self, user_id, service_name, value):
        user_id = ObjectId(user_id)

        # Fetch payment wallet
        payment = self.db.payment.find_one({"userId": user_id})
        if not payment:
            return None, "Payment record not found"

        wallet = payment.get("collaboratorWallet", {})
        balance = wallet.get("walletBalance", 0)

        if balance < int(value):
            return None, "Insufficient wallet balance"

        coupon_code = self._generate_code()

        coupon_data = {
            "userId": user_id,
            "couponCode": coupon_code,
            "serviceName": service_name,
            "value": int(value),
            "used": False,
            "createdAt": datetime.utcnow()
        }

        self.db.coupons.insert_one(coupon_data)

        # Add to payment collection
        self.db.payment.update_one(
            {"userId": user_id},
            {
                "$push": {
                    "collaboratorWallet.coupens": coupon_data
                },
                "$inc": {
                    "collaboratorWallet.walletBalance": -int(value)
                },
                "$set": {
                    "collaboratorWallet.updatedAt": datetime.utcnow()
                }
            }
        )

        # Add to service collection (optional if you have userId in service doc)
        service_doc = self.db.service.find_one({"_id": user_id})
        if service_doc:
            print("Pushing to service:", coupon_data) 
            self.service_provided_model.push_coupon_to_service(user_id, coupon_data)
        else:
            print("⚠️ Service document not found for user:", user_id)
        return {
            "couponCode": coupon_code,
            "walletBalance": balance - int(value)
        }, None

    def mark_coupon_used(self, coupon_code):
        # Mark as used in coupons
        result = self.db.coupons.update_one(
            {"couponCode": coupon_code, "used": False},
            {"$set": {"used": True, "usedAt": datetime.utcnow()}}
        )
        if result.matched_count == 0:
            return False, "Coupon not found or already used"

        # Remove from payment coupens array
        self.db.payment.update_many(
            {"collaboratorWallet.coupens.couponCode": coupon_code},
            {"$pull": {"collaboratorWallet.coupens": {"couponCode": coupon_code}}}
        )

        # Remove from service coupens array
        self.db.service.update_many(
            {"coupens.couponCode": coupon_code},
            {"$pull": {"coupens": {"couponCode": coupon_code}}}
        )

        return True, None