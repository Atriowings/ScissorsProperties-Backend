from app.model_controller.user_course_model import UserCourseModel

class UserCourseService:
    def __init__(self, db):
        self.user_course_model = UserCourseModel(db)

    def create_course(self, course_data):
        return self.user_course_model.add_course(course_data)

    def list_courses(self):
        return self.user_course_model.get_all_courses()