from flask import Blueprint
from app.admin_controller.service_provided import (
    service_create, service_login, service_forgot_password, service_reset_password,service_logout,
    get_all_login_coupons,generate_service_coupon,use_coupon
    )

service_bp = Blueprint('service_bp', __name__)

service_bp.route('/create-service', methods=['POST'])(service_create)
service_bp.route('/service-login', methods=['POST'])(service_login)
service_bp.route('/service-logout', methods=['GET'])(service_logout)
# service_bp.route('/service-change-password', methods=['PUT'])(service_change_password)
service_bp.route('/service-forgot-password', methods=['POST'])(service_forgot_password)

service_bp.route('/service-reset-password', methods=['POST'])(service_reset_password)

service_bp.route("/generate", methods=["POST"])(generate_service_coupon)
service_bp.route('/coupon-use', methods=['POST'])(use_coupon)