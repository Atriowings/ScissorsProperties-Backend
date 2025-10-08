from app.model_controller.user_service_model import UserServiceModel

class UserService:
    def __init__(self, db):
        self.user_service_model = UserServiceModel(db)

    def create_service(self, service_data):
        return self.user_service_model.add_service(service_data)

    def list_services(self):
        return self.user_service_model.get_all_services()