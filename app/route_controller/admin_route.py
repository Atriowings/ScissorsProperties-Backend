from flask import Blueprint
from app.admin_controller.admin import (
    admin_create, admin_login, forgot_password, change_password, reset_password,
    get_all_login_requests,get_user_and_payment_data,get_all_plans_requests,get_all_collaborators,
    get_partner_overview,handle_user_request, mark_full_payment, give_monthly_commission, list_partners,
    admin_logout,validate_admin_id,toggle_user_and_partner_status,admin_approve_plot_payment,admin_decline_plot
)

admin_bp = Blueprint('admin_bp', __name__)

admin_bp.route('/create-admin', methods=['POST'])(admin_create)
admin_bp.route('/admin-login', methods=['POST'])(admin_login)
admin_bp.route('/admin-logout', methods=['GET'])(admin_logout)
admin_bp.route('/admin-change-password', methods=['PUT'])(change_password)
admin_bp.route('/admin-forgot-password', methods=['POST'])(forgot_password)
admin_bp.route('/admin-reset-password', methods=['POST'])(reset_password)

admin_bp.route('/all-requests', methods=['GET'])(get_all_login_requests)
admin_bp.route('/plan-requests', methods=['GET'])(get_all_plans_requests)
admin_bp.route('/handle-request', methods=['POST'])(handle_user_request)
admin_bp.route("/complete-full-payment", methods=["POST"])(mark_full_payment)
admin_bp.route("/commission", methods=["POST"])(give_monthly_commission)

admin_bp.route("/partners", methods=["GET"])(list_partners)
admin_bp.route('/partner-overview', methods=['GET'])(get_partner_overview)
admin_bp.route('/collaborators', methods=['GET'])(get_all_collaborators)

admin_bp.route('/get_all', methods=['GET'])(get_user_and_payment_data)
admin_bp.route('/validate-id', methods=['GET'])(validate_admin_id)
admin_bp.route("/toggle-status", methods=["POST"])(toggle_user_and_partner_status)
admin_bp.route('/approve-plot-payment', methods=['POST'])(admin_approve_plot_payment)
admin_bp.route('/decline-plot', methods=['POST'])(admin_decline_plot)

