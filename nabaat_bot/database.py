import pymongo
from datetime import datetime
import os


class Database:
    """Instances establish a connection with the database 
    (speciefied by env variable MONGODB_URI) and offers 
    some utility functions
    """
    def __init__(self) -> None:
        self.client = pymongo.MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["nabaatBot"]  # database name
        self.user_collection = self.db["userCollection"]
        self.bot_collection = self.db["botCollection"]
        self.activity_collection = self.db["activityCollection"]
        self.token_collection = self.db["tokenCollection"]
        self.dialog_collection = self.db["dialogCollection"]
        self.wip_questions_collection = self.db["wipQuestionsCollection"]
        self.fin_questions_collection = self.db["finQuestionsCollection"]
        self.required_fields = ["_id", "username", "name", "phone-number"]

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
        return self.bot_collection.find_one( {"name": "admins-list"} )["admins"]

    def get_experts(self) -> dict:
        """returns a dict containing expert & groupID as a key/value pair"""
        return self.bot_collection.find_one( {"name": "experts-list"} )["experts"]

    def add_new_user(
        self,
        user_id: int,
        username: str = "",
        first_seen: str = datetime.now().strftime("%Y-%m-%d %H:%M")
    ) -> None:
        user_dict = {
            "_id": user_id,
            "username": username,
            "first-seen": first_seen,
            "blocked": False
        }

        if not self.check_if_user_exists(user_id=user_id):
            self.user_collection.insert_one(user_dict)

    def add_new_question(self, user_id: int, question: str, answer: str) -> None:
        # if not self.wip_questions_collection.find_one( { "_id": user_id } ):
        self.wip_questions_collection.update_one(
            {"_id": user_id},
            {"$set": {question: answer}},
            upsert=True
        )

    def check_in_progress_qusetions(self, user_id: int) -> bool:
        if self.wip_questions_collection.find_one( { "_id": user_id} ):
            return True
        else:
            return False
        
    def move_question_to_finished_collection(self, user_id: int) -> None:
        document = self.wip_questions_collection.find_one( { "_id": user_id } )
        document["userID"] = document.pop("_id")
        self.fin_questions_collection.insert_one(document)

    def del_from_wip_collection(self, user_id) -> None:
        self.wip_questions_collection.delete_one( { "_id": user_id } )

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

    def save_coupon(self, text, value):
        if not self.bot_collection.find_one( {"_id": "coupons"} ):
            self.bot_collection.insert_one({"_id": "coupons", 'values': [{text: float(value)}]})
            return True
        else:
            coupons_doc = self.bot_collection.find_one( {"_id": "coupons"} )
            coupons = [list(coupon.keys())[0] for coupon in coupons_doc["values"]]
            if text in coupons:
                return False
            else:
                self.bot_collection.update_one({"_id": "coupons"}, {"$push": {'values': {text: float(value)} }})
                return True

    def verify_coupon(self, coupon: str):
        coupons_doc = self.bot_collection.find_one( {"_id": "coupons"} )
        if not coupons_doc:
            return False
        coupons = [list(coupon.keys())[0] for coupon in coupons_doc["values"]]
        if coupon in coupons:
            return True
        else: return False
    
    def apply_coupon(self, coupon: str, original: float) -> float:
        coupons_doc = self.bot_collection.find_one( {"_id": "coupons"} )
        coupons = coupons_doc["values"]
        for item in coupons:
            coupon_value = item.get(coupon)
            if coupon_value:
                new_value = original - coupon_value
                return new_value
        return original

    def log_payment( self,
                     user_id: int,
                     used_coupon: str = None,
                     reason: str = 'subscription',
                     amount: float = 500000.0,
                     verified: bool = False,
                     code: str = ""):
        current_time = datetime.now().strftime("%Y%m%d %H:%M")
        payment_dict = {
            'code': code,
            'time-approved': current_time,
            'reason': reason,
            'amount': amount,
            'coupon': used_coupon,
            'verified': verified
        }
        self.set_user_attribute(user_id, 'payments', payment_dict, True)

    def add_coupon_to_payment_dict(self, user_id: int, code: str, coupon: str) -> None:
        filter_query = {'_id': user_id,
                        'payments': {'$elemMatch': {'code': code} } }
        update_query = {'$set': { 'payments.$.coupon': coupon } }
        self.user_collection.update_one(filter_query, update_query)

    def modify_final_price_in_payment_dict(self, user_id: int, code: str, final_price: float) -> None:
        filter_query = {'_id': user_id,
                        'payments': {'$elemMatch': {'code': code} } }
        update_query = {'$set': { 'payments.$.amount': final_price } }
        self.user_collection.update_one(filter_query, update_query)

    def get_final_price(self, user_id: int, code: str):
        document = self.user_collection.find_one( {'_id': user_id,
                                        'payments': {'$elemMatch': {'code': code} }} )
        payment = next((payment for payment in document['payments'] if payment['code'] == code), None)
        return payment['amount']

    def verify_payment(self, user_id: int, code: str):
        filter_query = {'_id': user_id,
                        'payments': {'$elemMatch': {'code': code} } }
        update_query = {'$set': { 'payments.$.verified': True } }
        self.user_collection.update_one(filter_query, update_query)
        self.set_user_attribute(user_id, 'has-verified-payments', True)
        
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
    
   