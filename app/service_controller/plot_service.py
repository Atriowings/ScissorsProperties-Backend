from datetime import datetime
from bson import ObjectId
from app.utils import convert_objectid_to_str,send_plot_declined_email
from app.model_controller.create_plots_model import PlotModel
from app.model_controller.payment_model import Payment

class PlotService:
    def __init__(self, db):
        self.db = db
        self.plots = db.plots
        self.plot_model = PlotModel(db)
        self.payment_model=Payment(db)

    def request_plot(self, user_id, plot_type, upi, upi_mobile):
        now = datetime.utcnow()
        request_data = {
            "userId": ObjectId(user_id),
            "planType": plot_type,
            "upi": upi,
            "upiMobileNumber": upi_mobile,
            "plotStatus": "Pending",
            "emiPaymentRequested": False,
            "requestedEmiPaymentAmount": 0,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        result=self.plots.insert_one(request_data)
        plot_id = result.inserted_id  


        self.db.payment.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "additionalPlotPurchase": {
                        "purcharseRequested": True,
                        "plotStatus": "Pending", 
                        "initialPlanType": plot_type,
                        "planType": plot_type,
                        "sq_feet": 1200 if plot_type == "A" else None,
                        "planAmount": 600000 if plot_type == "A" else None,
                        "upi": upi,
                        "upiMobileNumber": upi_mobile,
                        "plotId": plot_id,
                        "planAorBaccepted": False,
                    },
                    "updatedAt": now
                }
            }
        )

        return convert_objectid_to_str(request_data)


    def approve_plot(self, plot_id):
        plot = self.plots.find_one({
            "_id": ObjectId(plot_id),
            "plotStatus": "Pending"
        })

        if not plot:
            return None, "Plot not found or already approved."

        final_plot = self.plot_model.create_plot(plot)
        if not final_plot:
            return None, "Invalid plot type."

        final_plot["plotStatus"] = "Approved"

        # ✅ Set full payment status based on plan
        if final_plot["planType"] == "C":
            paid_months = final_plot.get("paidMonths", 0)
            total_months = final_plot.get("totalMonths", 0)
            final_plot["fullPaymentStatus"] = "Completed" if paid_months >= total_months else "Pending"
        else:
            final_plot["fullPaymentStatus"] = "Pending"

        # ✅ Update the plot in 'plots' collection
        self.plots.update_one(
            {"_id": ObjectId(plot_id)},
            {"$set": final_plot}
        )

        # ✅ Check if this is an additional plot
        payment_doc = self.db.payment.find_one({
            "userId": plot["userId"],
            "additionalPlotPurchase.plotId": ObjectId(plot_id)
        })

        if payment_doc:
            # ✅ Update payment document with approved status
            self.db.payment.update_one(
                {"userId": plot["userId"], "additionalPlotPurchase.plotId": ObjectId(plot_id)},
                {
                    "$set": {
                        "additionalPlotPurchase.plotStatus": "Approved",
                    }
                }
            )

            # ✅ If it's Plan C and an additional plot, give commission and clear fields
            if final_plot["planType"] == "C":
                user = self.db.users.find_one({"_id": plot["userId"]})
                referral_id = user.get("referredById") if user else None

                if referral_id:
                    partner = self.db.partners.find_one({"myReferralId": referral_id})
                    if partner:
                        self.db.partners.update_one(
                            {"userId": partner["userId"], "myReferralId": referral_id},
                            {
                                "$inc": {
                                    "commissionWallet.commissionWalletBalance": 1500
                                },
                                "$push": {
                                    "commissionHistory": {
                                        "amount": 1500,
                                        "date": datetime.utcnow()
                                    }
                                }
                            }
                        )

                # ✅ Clear additional plot purchase fields
                self.db.payment.update_one(
                    {"userId": plot["userId"], "additionalPlotPurchase.plotId": ObjectId(plot_id)},
                    {
                        "$unset": {
                            "additionalPlotPurchase.planType": "",
                            "additionalPlotPurchase.planAmount": "",
                            "additionalPlotPurchase.sq_feet": "",
                            "additionalPlotPurchase.upi": "",
                            "additionalPlotPurchase.upiMobileNumber": "",
                            "additionalPlotPurchase.plots": "",
                            "additionalPlotPurchase.plotId": "",
                            "additionalPlotPurchase.plotStatus": "",
                            "additionalPlotPurchase.purcharseRequested": ""
                        }
                    }
                )

        return convert_objectid_to_str(final_plot), None

    def approve_plot_payment(self, user_id, plot_id):
        plot = self.plots.find_one({
            "_id": ObjectId(plot_id),
            "userId": ObjectId(user_id)
        })

        if not plot:
            return None, "Plot not found"

        if plot.get("planType") not in ["A", "B"]:
            return None, "Only Plan A and B are allowed"

        if plot.get("fullPaymentStatus") == "Completed":
            return None, "Full payment already approved"

        plan_type = plot.get("planType")
        plan_amount = 600000 if plan_type == "A" else 300000
        commission_amount = plan_amount * 0.10  # 10%
        print(commission_amount)
        # ✅ Apply referral commission (same logic as in C EMI flow)
        user = self.db.users.find_one({"_id": ObjectId(user_id)})
        referral_id = user.get("referredById") if user else None
        if referral_id:
            partner = self.db.partners.find_one({"myReferralId": referral_id})
            print(partner)
            if partner:
                print("partner exists")
                partner_id = partner["userId"]

                self.db.partners.update_one(
                    {"userId": partner_id, "myReferralId": referral_id},
                    {
                        "$inc": {
                            "commissionWallet.commissionWalletBalance": commission_amount
                        },
                        "$push": {
                            "commissionHistory": {
                                "amount": commission_amount,
                                "date": datetime.utcnow()
                            }
                        }
                    }
                )
        # Update payment-related fields only
        updated_fields = {
            "fullPaymentStatus": "Completed",
            "emiPaymentRequested": False,
            "paidAmount": 600000 if plot["planType"] == "A" else 300000,
            "paidMonths": 60,
            "pendingMonths": 0,
            "pendingMonthsList": [],
            "nextDue": 0,
            "nextDueMonth": None,
            "nextDueDate": None,
            "planAorBaccepted": True,
            "updatedAt": datetime.utcnow()
        }

        self.plots.update_one(
            {"_id": ObjectId(plot_id)},
            {"$set": updated_fields}
        )
        # ✅ Empty additionalPlotPurchase after Plan A/B second approval
        self.db.payment.update_one(
            {"userId": ObjectId(user_id)},
            {
                "$set": {
                    "additionalPlotPurchase.purcharseRequested": False,
                    "additionalPlotPurchase.plotStatus": None,
                    "additionalPlotPurchase.planType": None,
                    "additionalPlotPurchase.sq_feet": None,
                    "additionalPlotPurchase.planAmount": None,
                    "additionalPlotPurchase.upi": None,
                    "additionalPlotPurchase.upiMobileNumber": None,
                    "additionalPlotPurchase.plotId": None,
                    "additionalPlotPurchase.plots": None,
                    "additionalPlotPurchase.planAorBaccepted": False
                }
            }
        )

        return {
            "plot_id": str(plot_id),
            "user_id": str(user_id),
            "status": "Completed"
        }, None

    def decline_plot(self, plot_id):
        plot = self.plots.find_one({
            "_id": ObjectId(plot_id),
            "plotStatus": "Pending",
            "emiPaymentRequested": True
        })

        if not plot:
            return None, "Plot not found or already processed"

        user_id = plot["userId"]
        plan_type = plot.get("planType")

        # 1. Update plot status to "Declined"
        self.plots.update_one(
            {"_id": ObjectId(plot_id)},
            {
                "$set": {
                    "plotStatus": "Declined",
                    "emiPaymentRequested": False,
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        # Clear additionalPlotPurchase
        self.db.payment.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "additionalPlotPurchase.purcharseRequested": False,
                    "additionalPlotPurchase.plotStatus": None,
                    "additionalPlotPurchase.planType": None,
                    "additionalPlotPurchase.sq_feet": None,
                    "additionalPlotPurchase.planAmount": None,
                    "additionalPlotPurchase.upi": None,
                    "additionalPlotPurchase.upiMobileNumber": None,
                    "additionalPlotPurchase.plotId": None,
                    "additionalPlotPurchase.plots": None
                }
            }
        )

        # 3. Remove plot from user’s plot list if it exists there
        self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$pull": {
                    "plots": plot.get("plots")
                }
            }
        )

        # 4. Optional: Delete the declined plot document itself (if you want it fully removed)
        self.plots.delete_one({"_id": ObjectId(plot_id)})

        # 5. Send email to the user
        user = self.db.users.find_one({"_id": user_id})
        if user:
            send_plot_declined_email({
                "user_name": user.get("userName") or user.get("user_name"),
                "email": user.get("email"),
                "plan_type": plan_type
            })

        return {"plot_id": str(plot_id), "status": "Declined"}, None