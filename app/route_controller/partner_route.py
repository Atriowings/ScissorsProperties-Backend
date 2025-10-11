from flask import Blueprint
from app.auth_controller.partner_controller import (
    handle_partner_request,partner_dashboard,approve_partner_request,
    decline_partner_request,request_partner_wallet_withdrawal,
    approve_partner_wallet_withdrawal,decline_partner_wallet_withdrawal
    
)

partner_bp = Blueprint("partner_bp", __name__)

partner_bp.route("/api/approve", methods=["POST"])(approve_partner_request)
partner_bp.route("/api/decline", methods=["POST"])(decline_partner_request)
partner_bp.route("/api/confirm", methods=["POST"])(handle_partner_request)
# partner_bp.route("/refer-user", methods=["POST"])(refer_user)

# partner_bp.route("/make", methods=["POST"])(make_partner)
partner_bp.route("/api/partner-dashboard", methods=["GET"])(partner_dashboard)
# partner_bp.route("/api/commission", methods=["POST"])(give_monthly_commission)


partner_bp.route("/api/wallet-withdraw-request", methods=["POST"])(request_partner_wallet_withdrawal)
partner_bp.route("/api/wallet-withdraw-approve", methods=["POST"])(approve_partner_wallet_withdrawal)
partner_bp.route("/api/wallet-withdraw-decline", methods=["POST"])(decline_partner_wallet_withdrawal)