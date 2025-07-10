from datetime import datetime
from bson import ObjectId

class CouponModel:
    def __init__(self, db):
        self.coupons = db.coupons

    def create_coupon(self, user_id, coupon_code, service_name, value):
        return self.coupons.insert_one({
            "userId": ObjectId(user_id),
            "couponCode": coupon_code,
            "serviceName": service_name,
            "value": value,
            "used": False,
            "createdAt": datetime.utcnow()
        })

    def mark_as_used(self, coupon_code):
        return self.coupons.update_one(
            {"couponCode": coupon_code},
            {"$set": {"used": True, "usedAt": datetime.utcnow()}}
        )