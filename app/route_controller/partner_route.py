from flask import Blueprint
from app.auth_controller.partner_controller import (
    refer_user,handle_partner_request,partner_dashboard,approve_partner_request,decline_partner_request    
)

partner_bp = Blueprint("partner_bp", __name__)

partner_bp.route("/approve", methods=["POST"])(approve_partner_request)
partner_bp.route("/decline", methods=["POST"])(decline_partner_request)
partner_bp.route("/confirm", methods=["POST"])(handle_partner_request)

# partner_bp.route("/make", methods=["POST"])(make_partner)
partner_bp.route("/refer", methods=["POST"])(refer_user)
partner_bp.route("/dashboard", methods=["GET"])(partner_dashboard)
# partner_db.route("/commission", methods=["POST"])(give_monthly_commission)