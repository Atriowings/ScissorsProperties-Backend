from flask import Blueprint
from app.auth_controller.auth import (
    Signup, Login,
    Forgot_password
    ,customer_dashboard,Change_password,Reset_password,Complete_payment,get_lucky_charm_status,
    get_wallet_balance,transfer_to_course,transfer_to_service,request_wallet_addition,approve_wallet_addition
)

auth_bp = Blueprint('auth_bp', __name__)

auth_bp.route('/register', methods=['POST'])(Signup)
auth_bp.route('/login', methods=['POST'])(Login)
auth_bp.route('/forgot-password', methods=['POST'])(Forgot_password)
auth_bp.route('/reset-password', methods=['POST'])(Reset_password)
auth_bp.route('/change-password', methods=['POST'])(Change_password)

auth_bp.route('/complete-payment', methods=['POST'])(Complete_payment)
auth_bp.route('/user/lucky-charm-status', methods=['GET'])(get_lucky_charm_status)
auth_bp.route('/current-user', methods=['GET'])(customer_dashboard)

auth_bp.route("/wallet-balance", methods=["POST"])(get_wallet_balance)
auth_bp.route("/wallet/transfer-service", methods=["POST"])(transfer_to_service)
auth_bp.route("/wallet/transfer-course", methods=["POST"])(transfer_to_course)

auth_bp.route('/wallet/request-add-money', methods=['POST'])(request_wallet_addition)
auth_bp.route('/wallet/approve-add-money', methods=['POST'])(approve_wallet_addition)