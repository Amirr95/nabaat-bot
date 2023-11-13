import pymongo
import gridfs
from datetime import datetime
from bson.objectid import ObjectId
import os


class Database:
    """Instances establish a connection with the database 
    (speciefied by env variable MONGODB_URI) and offers 
    some utility functions
    """
    def __init__(self) -> None:
        self.client = pymongo.MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["nabaatBot"]  # database name
        self.pictures_db_gridFS = gridfs.GridFS(self.client["pictures"])
        self.user_collection = self.db["userCollection"]
        self.bot_collection = self.db["botCollection"]
        self.activity_collection = self.db["activityCollection"]
        self.token_collection = self.db["tokenCollection"]
        self.dialog_collection = self.db["dialogCollection"]
        self.wip_questions = self.db["wipQuestionsCollection"]
        self.fin_questions = self.db["finQuestionsCollection"]
        self.required_fields = ["_id", "username", "name", "phone-number"]

    def save_pictures(self, question_id: ObjectId, pic_names: list[int]) -> None:
        """
        input: 
            - ObjectID of a document in finQuestionCollection.
            - list of picture names (message IDs)
            
        Will look for picture ids and save the pictures in mongodb.
        Saves the resulting ObjectIDs of the pictures in the question document.
        """
        for name in pic_names:
            with open(f"{name}.jpg", "rb") as photo:
                self.pictures_db_gridFS.put(photo, questionID=question_id)
            os.system(f"rm {name}.jpg")
    
    def check_if_user_exists(self, user_id: int, raise_exception: bool = False) -> bool:
        if self.user_collection.count_documents({"_id": user_id}) > 0:
            return True
        else:
            if raise_exception:
                raise ValueError(f"User {user_id} does not exist")
            else:
                return False

    def check_if_user_is_registered(self, user_id: int) -> bool:
        if not self.check_if_user_exists(user_id=user_id):
            return False
        else:
            document = self.user_collection.find_one( {"_id": user_id} )
            if all(key in document for key in self.required_fields):
                return True
            else:
                return False

    def get_admins(self) -> list:
        """returns a list of admin IDs"""
        document = self.bot_collection.find_one( {"name": "admins-list"} )
        if document:
            return document.get("admins")
        else: 
            return []
            
    def get_experts(self) -> dict:
        """returns a dict containing expert & groupID as a key/value pair"""
        document = self.bot_collection.find_one( {"name": "experts-list"} )
        if document:
            return document.get("experts")
        else: 
            return {}
            
    def get_developers(self) -> list:
        """returns a list of developer IDs. Used to send them error messages"""
        document = self.bot_collection.find_one( {"name": "developers-list"} )
        if document:
            return document.get("developers")
        else: 
            return []
            
    def get_menu_cmds(self) -> list:
        """returns list of bot commands. Used to end ongoing conversations if encountered."""
        document = self.bot_collection.find_one( {"name": "commands-list"} )
        if document:
            return document.get("commands")
        else: 
            return []
        
    def add_new_user(
        self,
        user_id: int,
        username: str = "",
        first_seen: str = datetime.now().strftime("%Y%m%d %H:%M")
    ) -> None:
        user_dict = {
            "_id": user_id,
            "username": username,
            "first-seen": first_seen,
            "blocked": False
        }

        if not self.check_if_user_exists(user_id=user_id):
            self.user_collection.insert_one(user_dict)

    def add_new_question(self, user_id: int, question_name: str, question: str, answer: str) -> None:
        # if not self.wip_questions_collection.find_one( { "_id": user_id } ):
        self.wip_questions.update_one(
            {"_id": user_id},
            {"$set": {question_name: {question: answer}}},
            upsert=True
        )

    def check_in_progress_qusetions(self, user_id: int) -> bool:
        if self.wip_questions.find_one( { "_id": user_id} ):
            return True
        else:
            return False
        
    def move_question_to_finished_collection(self, user_id: int) -> ObjectId:
        """After a nabaat expert sends their final advice, this function removes the question document from wip_collection
        and moves it to fin_collection and returns the ObjectId of the inserted document
        """
        document = self.wip_questions.find_one( { "_id": user_id } )
        document["userID"] = document.pop("_id")
        res = self.fin_questions.insert_one(document)
        return res.inserted_id

    def del_from_wip_collection(self, user_id) -> None:
        self.wip_questions.delete_one( { "_id": user_id } )

    # def current_question_index(self, user_id):
    #     user_doc = self.user_collection.find_one({ "_id": user_id })
    #     if user_doc.get("questions"):
    #         return len(user_doc.get("questions")) - 1

    def add_token(self, user_id: int, value: str):
        token_dict = {
            "owner": user_id,
            "token-value": value,
            "time-created": datetime.now().strftime("%Y%m%d %H:%M"),
            "used-by": [],
        }
        self.token_collection.insert_one(token_dict)

    def log_token_use(self, user_id: int, value: str) -> int:
        token_document = self.token_collection.find_one({ "token-value": value })
        if token_document:
            owner = token_document.get("owner")
            self.token_collection.update_one({"token-value": value}, {"$push": {"used-by": user_id}})
            self.user_collection.update_one({"_id": user_id}, {"$set": {"invited-by": owner}})

    def calc_token_number(self, value: str):
        token_document = self.token_collection.find_one({ "token-value": value })
        return len(token_document['used-by'])

    def calc_user_tokens(self, user_id: int) -> int:
        user_tokens = self.token_collection.find( {"owner": user_id} )
        num = 0
        if user_tokens:            
            for token in user_tokens:
                num += len(token["used-by"])
        return num

    def get_user_attribute(self, user_id: int, key: str):
        self.check_if_user_exists(user_id=user_id, raise_exception=True)
        user_dict = self.user_collection.find_one({"_id": user_id})

        if key not in user_dict:
            return None
        return user_dict[key]
    
    def set_user_attribute(self, user_id: int, key: str, value: any, array: bool = False):
        self.check_if_user_exists(user_id=user_id, raise_exception=True)
        if not array:
            self.user_collection.update_one({"_id": user_id}, {"$set": {key: value}})
        else:
            self.user_collection.update_one({"_id": user_id}, {"$push": {key: value}})

    def log_new_message(
        self,
        user_id,
        username: str = "",
        message: str = "",
        function: str = "",
    ):
        current_time = datetime.now().strftime("%Y%m%d %H:%M")
        dialog_dict = {
            "_id": user_id,
            "username": username,
            "message": [f"{current_time} - {function} - {message}"],
            "function": [function]
        }

        if not self.check_if_dialog_exists(user_id=user_id):
            self.dialog_collection.insert_one(dialog_dict)
        else:
            self.dialog_collection.update_one(
                {"_id": user_id}, {
                    "$push": {"message": f"{current_time} - {function} - {message}", "function": function}})
    
    def log_sent_messages(self, users: list, function: str = "") -> None:
        current_time = datetime.now().strftime("%Y%m%d %H:%M")
        usernames = [self.user_collection.find_one({"_id": user})["username"] for user in users]
        users = [str(user) for user in users]
        log_dict = {
            "time-sent": current_time,
            "type": "sent messages",
            "function-used": function,
            "number-of-receivers": len(users),
            "receivers": dict(zip(users, usernames))
        }
        self.bot_collection.insert_one(log_dict)

    def log_member_changes(
        self,
        members: int = 0,
        time: str = "",
    ):
        bot_members_dict = {
            "num-members": [members],
            "time-stamp": [time]
        }

        if self.bot_collection.count_documents({}) == 0:
            self.bot_collection.insert_one(bot_members_dict)
        else:
            self.bot_collection.update_one({}, {"$push": {"num-members": members, "time-stamp": time}})

    def log_activity(self, user_id: int, user_activity: str, provided_value: str = ""):
        activity = {
            "user_activity": user_activity,
            "name": "activity logs",
            "value": provided_value,
            "userID": user_id,
            "username": self.user_collection.find_one({"_id": user_id})["username"],
            "timestamp": datetime.now().strftime("%Y%m%d %H:%M")
        }
        self.activity_collection.insert_one(activity)
    
    def number_of_members(self) -> int:
        members = self.user_collection.distinct("_id")
        return len(members)
    
    def number_of_blocks(self) -> int:
        blocked_users = self.user_collection.count_documents({"blocked": True})
        return blocked_users
    
   