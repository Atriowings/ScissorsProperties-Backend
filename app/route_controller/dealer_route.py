from flask import Blueprint
from app.auth_controller.dealer_controller import (
    handle_dealer_request,dealer_dashboard,approve_dealer_request,
    decline_dealer_request,request_dealer_wallet_withdrawal,
    approve_dealer_wallet_withdrawal,decline_dealer_wallet_withdrawal
    
)

dealer_bp = Blueprint("dealer_bp", __name__)

dealer_bp.route("/approve", methods=["POST"])(approve_dealer_request)
dealer_bp.route("/decline", methods=["POST"])(decline_dealer_request)
dealer_bp.route("/confirm", methods=["POST"])(handle_dealer_request)
# dealer_bp.route("/refer-user", methods=["POST"])(refer_user)

# dealer_bp.route("/make", methods=["POST"])(make_dealer)
dealer_bp.route("/dealer-dashboard", methods=["GET"])(dealer_dashboard)
# dealer_bp.route("/commission", methods=["POST"])(give_monthly_commission)


dealer_bp.route("/wallet-withdraw-request", methods=["POST"])(request_dealer_wallet_withdrawal)
dealer_bp.route("/wallet-withdraw-approve", methods=["POST"])(approve_dealer_wallet_withdrawal)
dealer_bp.route("/wallet-withdraw-decline", methods=["POST"])(decline_dealer_wallet_withdrawal)