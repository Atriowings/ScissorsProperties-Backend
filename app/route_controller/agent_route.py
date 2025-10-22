from flask import Blueprint
from app.auth_controller.agent_controller import (
    handle_agent_request,agent_dashboard,approve_agent_request,
    decline_agent_request,request_agent_wallet_withdrawal,
    approve_agent_wallet_withdrawal,decline_agent_wallet_withdrawal
    
)

agent_bp = Blueprint("agent_bp", __name__)

agent_bp.route("/approve", methods=["POST"])(approve_agent_request)
agent_bp.route("/decline", methods=["POST"])(decline_agent_request)
agent_bp.route("/confirm", methods=["POST"])(handle_agent_request)
# agent_bp.route("/refer-user", methods=["POST"])(refer_user)

# agent_bp.route("/make", methods=["POST"])(make_agent)
agent_bp.route("/agent-dashboard", methods=["GET"])(agent_dashboard)
# agent_bp.route("/commission", methods=["POST"])(give_monthly_commission)


agent_bp.route("/wallet-withdraw-request", methods=["POST"])(request_agent_wallet_withdrawal)
agent_bp.route("/wallet-withdraw-approve", methods=["POST"])(approve_agent_wallet_withdrawal)
agent_bp.route("/wallet-withdraw-decline", methods=["POST"])(decline_agent_wallet_withdrawal)