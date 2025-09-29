from datetime import datetime
from bson import ObjectId



class UserCourseModel:
    def __init__(self, db):
        self.user_courses = db.userCourses

    def add_course(self, course_data):
        try:
            course_data["createdAt"] = datetime.utcnow()
            course_data["updatedAt"] = datetime.utcnow()
            result = self.user_courses.insert_one(course_data)
            return result.inserted_id, None  # ✅ Return as tuple (data, error)
        except Exception as e:
            return None, str(e)

    def get_all_courses(self):
        try:
            courses = list(self.user_courses.find())
            for course in courses:
                course["_id"] = str(course["_id"])
            return courses, None  # ✅ Also return tuple here
        except Exception as e:
            return None, str(e)