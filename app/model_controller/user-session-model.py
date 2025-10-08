from datetime import datetime

from app.utils import convert_objectid_to_str

class UserSession:
    def __init__(self, db):
        self.userSessions = db.userSessions

    def create(self, data):
        self.userSessions.insert_one(data)
        return

    def update(self, match, data):
        data['updatedAt'] = datetime.utcnow()
        self.userSessions.update_one(match, {'$set': data} )
        return
    
    def find_one(self, match):
        result = self.userSessions.find_one(match)
        return convert_objectid_to_str(result)
