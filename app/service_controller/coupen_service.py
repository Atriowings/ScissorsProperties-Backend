import random, string
from bson import ObjectId
from datetime import datetime
from app.service_controller.service_provider_service import ServiceProvide
from app.model_controller.coupen_model import CouponModel

class CouponService:
    def __init__(self, db):
        self.db = db
        self.service_provider_model = ServiceProvide(db)
        self.coupon_model = CouponModel(db)

    def _generate_code(self, length=8):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def generate_coupon(self, user_id, service_name, value, service_type):
        user_id = ObjectId(user_id)

        # Fetch payment wallet
        payment = self.db.payment.find_one({"userId": user_id})
        if not payment:
            return None, "Payment record not found"

        wallet = payment.get("collaboratorWallet", {})
        course_balance = wallet.get("courseWalletBalance", 0)
        service_balance = wallet.get("serviceWalletBalance", 0)
        wallet_balance = course_balance + service_balance

        # 🔒 Validate service/coupon limit
        if service_type == "service":
            if float(value) > 5000:
                return None, "Service coupon price cannot exceed ₹5000"
            if service_balance < int(value):
                return None, "Insufficient service wallet balance"
        elif service_type == "course":
            if course_balance < int(value):
                return None, "Insufficient course wallet balance"
        else:
            return None, "Invalid service type"

        # 🎟️ Generate and prepare coupon
        coupon_code = self._generate_code()
        self.coupon_model.create_coupon(user_id, coupon_code, service_name, int(value), service_type)

        coupon_data = {
            "userId": user_id,
            "couponCode": coupon_code,
            "serviceName": service_name,
            "serviceType": service_type,
            "value": int(value),
            "used": False,
            "createdAt": datetime.utcnow()
        }

        self.db.coupons.insert_one(coupon_data)

        # 🧾 Prepare update payload
        update_dict = {
            "$push": {
                "collaboratorWallet.coupens": coupon_data
            },
            "$set": {
                "collaboratorWallet.updatedAt": datetime.utcnow()
            }
        }

        # 💰 Deduct from correct wallet
        if service_type == "service":
            update_dict["$inc"] = {
                "collaboratorWallet.serviceWalletBalance": -int(value),
                "collaboratorWallet.walletBalance": -int(value)
            }
        else:  # course
            update_dict["$inc"] = {
                "collaboratorWallet.courseWalletBalance": -int(value),
                "collaboratorWallet.walletBalance": -int(value)
            }

        self.db.payment.update_one(
            {"userId": user_id},
            update_dict
        )

        # 🌐 Optionally push to service-provider (global store)
        self.service_provider_model.push_coupon_global(user_id, coupon_data)

        return {
            "couponCode": coupon_code,
            "walletBalance": wallet_balance - int(value)
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