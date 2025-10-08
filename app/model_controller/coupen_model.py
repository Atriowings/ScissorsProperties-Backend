from datetime import datetime
from bson import ObjectId
import calendar

class CouponModel:
    def __init__(self, db):
        self.coupons = db.coupons

    def create_coupon(self, user_id, coupon_code, service_name, value, service_type):
        now = datetime.utcnow()
        coupon_data = {
            "userId": ObjectId(user_id),
            "couponCode": coupon_code,
            "serviceName": service_name,
            "value": value,
            "serviceType": service_type,
            "used": False,
            "createdAt": now
        }

        # Add expiry only for service-type
        if service_type == "service":
            year = now.year
            month = now.month
            last_day = min(30, calendar.monthrange(year, month)[1])  # handles Feb, etc.
            coupon_data["expiryDate"] = datetime(year, month, last_day)

        return self.coupons.insert_one(coupon_data)

    def mark_as_used(self, coupon_code):
        return self.coupons.update_one(
            {"couponCode": coupon_code},
            {"$set": {"used": True, "usedAt": datetime.utcnow()}}
        )
