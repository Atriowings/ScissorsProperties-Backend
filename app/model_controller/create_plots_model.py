from datetime import datetime, timedelta
from bson import ObjectId
from dateutil.relativedelta import relativedelta

class PlotModel:
    def __init__(self, db):
        self.plots = db.plots
        self.users = db.users
        self.payment = db.payment

    def get_last_plot_number(self):
        last_plot = self.plots.find_one(
            {"plots": {"$regex": "^P\\d{4}$"}},
            sort=[("plots", -1)]
        )
        return last_plot.get("plots") if last_plot else None

    def create_plot(self, plot):
        now = datetime.utcnow()
        last_plot = self.get_last_plot_number()
        plot_num = int(last_plot[1:]) + 1 if last_plot and last_plot[1:].isdigit() else 1
        plot_code = f"P{plot_num:04d}"

        plan_type = plot["planType"]
        upi = plot["upi"]
        upi_mobile = plot["upiMobileNumber"]

        if plan_type == "A":
            sq_feet = 1200
            total_amount = 600000
            paid_amount = 600000
            pending_amount = 0
            emi_type = False
            paid_months = 60
            pending_months = 0
            pending_list = []
            next_due = 0
            next_due_month = None
            next_due_date = None

        elif plan_type == "B":
            sq_feet = 600
            total_amount = 300000
            paid_amount = 300000
            pending_amount = 0
            emi_type = False
            paid_months = 60
            pending_months = 0
            pending_list = []
            next_due = 0
            next_due_month = None
            next_due_date = None

        elif plan_type == "C":
            sq_feet = 600
            total_amount = 300000
            paid_amount = 5000  
            pending_amount = total_amount - paid_amount
            emi_type = True
            paid_months = 1
            pending_months = 59
            pending_list = self.generate_month_list(1)
            next_due = 5000
            next_due_month = pending_list[0]
            next_due_date = now.replace(day=1) + timedelta(days=30)

        else:
            return None

        base_plot_data = {
            "plots": plot_code,
            "planType": plan_type,
            "sq_feet": sq_feet,
            "planAmount": total_amount,
            "paidAmount": paid_amount,
            "pendingAmount": pending_amount,
            "fullPaymentStatus": "Pending",
            "plotStatus": "Approved",
            "emiPaymentRequested": False,
            "requestedEmiPaymentAmount": 0,
            "upi": upi,
            "upiMobileNumber": upi_mobile,
            "totalMonths": 60,
            "paidMonths": paid_months,
            "pendingMonths": pending_months,
            "pendingMonthsList": pending_list,
            "nextDue": next_due,
            "nextDueMonth": next_due_month,
            "nextDueDate": next_due_date,
            "emiType": emi_type,
            "canParticipateLuckyDraw": True,
            "luckyDrawMessage": "Eligible",
            "createdAt": now,
            "updatedAt": now
        }

        if plot.get("isAdditionalPlot"):
            base_plot_data["plotId"] = plot.get("plotId")  # Store ID if needed for backend tracing
            return base_plot_data  # Just return plot dict to be appended under `additionalPlots`

        # Else it's first plot
        base_plot_data["userId"] = plot["userId"]
        return base_plot_data

        
    def update_user_plots(self, user_id, new_plot):
        user_id = ObjectId(user_id)

        # Step 1: Update in users collection
        user = self.users.find_one({"_id": user_id})
        if not user:
            print(f"❌ User not found for user_id: {user_id}")
            return

        existing_user_plots = user.get("plots")
        updated_user_plots = (
            [new_plot] if not existing_user_plots else
            ([existing_user_plots] if isinstance(existing_user_plots, str) else existing_user_plots + [new_plot])
        )

        self.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "plots": updated_user_plots,
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        # Step 2: Update in payment collection
        payment_doc = self.payment.find_one({"userId": user_id})
        if not payment_doc:
            return

        existing_payment_plots = payment_doc.get("plots", [])
        updated_payment_plots = (
            [new_plot] if not existing_payment_plots else
            ([existing_payment_plots] if isinstance(existing_payment_plots, str) else existing_payment_plots + [new_plot])
        )

        # Step 3: Fetch plot data
        plot_data = self.plots.find_one({"plots": new_plot})
        if not plot_data:
            return

        sq_feet = plot_data.get("sq_feet")
        plan_type = plot_data.get("planType")
        plan_amount = plot_data.get("planAmount")
        upi = plot_data.get("upi")
        upi_mobile = plot_data.get("upiMobileNumber")

        # Step 4: Build history entry
        history_record = {
            "plot": new_plot,
            "planType": plan_type,
            "sq_feet": sq_feet,
            "planAmount": plan_amount,
            "upi": upi,
            "upiMobileNumber": upi_mobile,
            "addedOn": datetime.utcnow()
        }

        # Step 5: Conditional update of `additionalPlotPurchase`
        additional_plot_update = {
            "updatedAt": datetime.utcnow()
        }

        if plan_type in ["A", "B"]:
            additional_plot_update.update({
                "additionalPlotPurchase.plots": None,
                "additionalPlotPurchase.planType": None,
                "additionalPlotPurchase.sq_feet": None,
                "additionalPlotPurchase.planAmount": None,
                "additionalPlotPurchase.upi": None,
                "additionalPlotPurchase.upiMobileNumber": None,
                "additionalPlotPurchase.purcharseRequested": False,
                "additionalPlotPurchase.plotStatus": "Pending",
                "updatedAt": datetime.utcnow()
            })

        self.payment.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "plots": updated_payment_plots,
                    **additional_plot_update
                },
                "$push": {
                    "additionalPlotPurchase.purcharseHistory": history_record
                }
            }
        )

    def generate_month_list(self, start_index=0):
        now = datetime.utcnow().replace(day=1)
        return [(now + relativedelta(months=i)).strftime("%B %Y") for i in range(start_index, 60)]
        
    def delete_by_user_id(self, user_id):
        return self.plots.delete_many({"userId": ObjectId(user_id)})