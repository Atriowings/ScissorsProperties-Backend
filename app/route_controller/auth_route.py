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

auth_bp.route('/api/health', methods=['GET'])(lambda: response_with_code(200, "Server is running"))
auth_bp.route('/api/register', methods=['POST'])(Signup)
auth_bp.route('/api/login', methods=['POST'])(Login)
auth_bp.route('/api/forgot-password', methods=['POST'])(Forgot_password)
auth_bp.route('/api/reset-password', methods=['POST'])(Reset_password)
auth_bp.route('/api/change-password', methods=['POST'])(Change_password)

auth_bp.route('/api/complete-payment', methods=['POST'])(Complete_payment)
# auth_bp.route('/api/pay-emi', methods=['POST'])(pay_emi_amount)
auth_bp.route('/api/current-user', methods=['GET'])(customer_dashboard)

auth_bp.route("/api/wallet-balance", methods=["POST"])(get_wallet_balance)
auth_bp.route("/api/wallet/transfer-service", methods=["POST"])(transfer_to_service)
auth_bp.route("/api/wallet/transfer-course", methods=["POST"])(transfer_to_course)
auth_bp.route('/api/wallet/request-add-money', methods=['POST'])(request_wallet_addition)
auth_bp.route('/api/wallet/approve-add-money', methods=['POST'])(approve_wallet_addition)
# auth_bp.route('/api/wallet/decline-add-money', methods=['POST'])(decline_wallet_addition)
auth_bp.route("/api/wallet/course-to-service-auto", methods=["POST"])(course_to_service_transfer)

auth_bp.route('/api/pay-emi', methods=['POST'])(pay_emi_amount)
auth_bp.route('/api/approve-emi', methods=['POST'])(approve_emi)
auth_bp.route('/api/decline-emi', methods=['POST'])(decline_emi)

auth_bp.route('/api/user/lucky-charm-status', methods=['POST'])(get_lucky_charm_status)
auth_bp.route('/api/request-plot', methods=['POST'])(request_plot)
auth_bp.route('/api/approve-plot', methods=['POST'])(approve_plot)

auth_bp.route('/api/collaborator/request-withdraw', methods=['POST'])(request_collaborator_withdrawal)
auth_bp.route('/api/collaborator/approve-withdraw', methods=['POST'])(approve_collaborator_withdrawal)
auth_bp.route('/api/collaborator/decline-withdraw', methods=['POST'])(decline_collaborator_withdrawal)