from flask import Blueprint
from app.auth_controller.auth import (
    Signup, Login,
    Forgot_password,customer_dashboard,Change_password,Reset_password,Complete_payment,
    get_wallet_balance,transfer_to_course,transfer_to_service,request_wallet_addition,
    approve_wallet_addition,course_to_service_transfer,pay_emi_amount,approve_emi,get_lucky_charm_status,
    request_plot,approve_plot,decline_emi,request_collaborator_withdrawal,approve_collaborator_withdrawal,decline_collaborator_withdrawal
)
from app.utils import response_with_code

auth_bp = Blueprint('auth_bp', __name__)

def health_check():
    return response_with_code(200, "Server is running")

def cors_test():
    return response_with_code(200, "CORS test successful")

auth_bp.route('/health', methods=['GET'])(health_check)
auth_bp.route('/test-cors', methods=['GET', 'POST', 'OPTIONS'])(cors_test)

auth_bp.route('/register', methods=['POST', 'OPTIONS'])(Signup)
auth_bp.route('/login', methods=['POST'])(Login)
auth_bp.route('/forgot-password', methods=['POST'])(Forgot_password)
auth_bp.route('/reset-password', methods=['POST'])(Reset_password)
auth_bp.route('/change-password', methods=['POST'])(Change_password)

auth_bp.route('/complete-payment', methods=['POST'])(Complete_payment)
# auth_bp.route('/pay-emi', methods=['POST'])(pay_emi_amount)
auth_bp.route('/current-user', methods=['GET'])(customer_dashboard)

auth_bp.route("/wallet-balance", methods=["POST"])(get_wallet_balance)
auth_bp.route("/wallet/transfer-service", methods=["POST"])(transfer_to_service)
auth_bp.route("/wallet/transfer-course", methods=["POST"])(transfer_to_course)
auth_bp.route('/wallet/request-add-money', methods=['POST'])(request_wallet_addition)
auth_bp.route('/wallet/approve-add-money', methods=['POST'])(approve_wallet_addition)
# auth_bp.route('/wallet/decline-add-money', methods=['POST'])(decline_wallet_addition)
auth_bp.route("/wallet/course-to-service-auto", methods=["POST"])(course_to_service_transfer)

auth_bp.route('/pay-emi', methods=['POST'])(pay_emi_amount)
auth_bp.route('/approve-emi', methods=['POST'])(approve_emi)
auth_bp.route('/decline-emi', methods=['POST'])(decline_emi)

auth_bp.route('/user/lucky-charm-status', methods=['POST'])(get_lucky_charm_status)
auth_bp.route('/request-plot', methods=['POST'])(request_plot)
auth_bp.route('/approve-plot', methods=['POST'])(approve_plot)

auth_bp.route('/collaborator/request-withdraw', methods=['POST'])(request_collaborator_withdrawal)
auth_bp.route('/collaborator/approve-withdraw', methods=['POST'])(approve_collaborator_withdrawal)
auth_bp.route('/collaborator/decline-withdraw', methods=['POST'])(decline_collaborator_withdrawal)