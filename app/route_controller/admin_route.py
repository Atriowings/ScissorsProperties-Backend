from flask import Blueprint
from app.admin_controller.admin import (
    admin_create, admin_login, forgot_password, change_password, reset_password,
    get_all_login_requests,get_user_and_payment_data,get_all_plans_requests,get_all_collaborators,
    get_partner_overview,handle_user_request, mark_full_payment, give_monthly_commission, list_partners,
    admin_logout,validate_admin_id,toggle_user_and_partner_status,admin_approve_plot_payment,admin_decline_plot
)

admin_bp = Blueprint('admin_bp', __name__)

admin_bp.route('/api/create-admin', methods=['POST'])(admin_create)
admin_bp.route('/api/admin-login', methods=['POST'])(admin_login)
admin_bp.route('/api/admin-logout', methods=['GET'])(admin_logout)
admin_bp.route('/api/admin-change-password', methods=['PUT'])(change_password)
admin_bp.route('/api/admin-forgot-password', methods=['POST'])(forgot_password)
admin_bp.route('/api/admin-reset-password', methods=['POST'])(reset_password)

admin_bp.route('/api/all-requests', methods=['GET'])(get_all_login_requests)
admin_bp.route('/api/plan-requests', methods=['GET'])(get_all_plans_requests)
admin_bp.route('/api/handle-request', methods=['POST'])(handle_user_request)
admin_bp.route("/api/complete-full-payment", methods=["POST"])(mark_full_payment)
admin_bp.route("/api/commission", methods=["POST"])(give_monthly_commission)

admin_bp.route("/api/partners", methods=["GET"])(list_partners)
admin_bp.route('/api/partner-overview', methods=['GET'])(get_partner_overview)
admin_bp.route('/api/collaborators', methods=['GET'])(get_all_collaborators)

admin_bp.route('/api/get_all', methods=['GET'])(get_user_and_payment_data)
admin_bp.route('/api/validate-id', methods=['GET'])(validate_admin_id)
admin_bp.route("/api/toggle-status", methods=["POST"])(toggle_user_and_partner_status)
admin_bp.route('/api/approve-plot-payment', methods=['POST'])(admin_approve_plot_payment)
admin_bp.route('/api/decline-plot', methods=['POST'])(admin_decline_plot)

