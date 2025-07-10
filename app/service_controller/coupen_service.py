import random, string
from bson import ObjectId
from datetime import datetime
from app.model_controller.service_provider_model import ServiceProvide

class CouponService:
    def __init__(self, db):
        self.db = db
        self.service_provided_model = ServiceProvide(db) 

    def _generate_code(self, length=8):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def generate_coupon(self, user_id, service_name, value):
        try:
            user_id = ObjectId(user_id)

            # Fetch payment wallet
            payment = self.db.payment.find_one({"userId": user_id})
            if not payment:
                return None, "Payment record not found"

            wallet = payment.get("collaboratorWallet", {})
            balance = wallet.get("serviceWalletBalance", 0)


            if balance < int(value):
                return None, "Insufficient wallet balance"

            coupon_code = self._generate_code()

            coupon_data = {
                "userId": str(user_id),
                "couponCode": coupon_code,
                "serviceName": service_name,
                "value": int(value),
                "used": False,
                "createdAt": datetime.utcnow()
            }

            # Store coupon in separate collection
            self.db.coupons.insert_one({
                **coupon_data,
                "userId": user_id  # Keep ObjectId here for internal use
            })

            # Update collaborator wallet
            self.db.payment.update_one(
                {"userId": user_id},
                {
                    "$push": {
                        "collaboratorWallet.coupens": coupon_data
                    },
                    "$inc": {
                        "collaboratorWallet.serviceWalletBalance": -int(value)
                    },
                    "$set": {
                        "collaboratorWallet.updatedAt": datetime.utcnow()
                    }
                }
            )

            # Optional: Push to service doc
            service_doc = self.db.service.find_one({"_id": user_id})
            if service_doc:
                print("✅ Pushing to service:", coupon_data)
                self.service_provided_model.push_coupon_to_service(user_id, coupon_data)
            else:
                print("⚠️ Service document not found for user:", user_id)

            # Return clean, frontend-usable response
            return {
                "couponCode": coupon_code,
                "walletBalance": balance - int(value)
            }, None

        except Exception as e:
            print("❌ Exception in generate_coupon:", str(e))
            return None, str(e)
