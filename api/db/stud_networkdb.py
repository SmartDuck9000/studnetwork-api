from pymongo import MongoClient
from db import config

client = MongoClient(host=config.DB_HOST, port=config.DB_PORT)
db = client[config.DB_NAME]


def add_user(user):
    if db.users.find_one({'vk_id': user['vk_id']}) is None:
        db.users.insert_one(user)
    elif user['type'] in ['simple', 'advanced']:
        update_user(user)


def add_group(group):
    if db.groups.find_one({'vk_id': group['vk_id']}) is None:
        db.groups.insert_one(group)


def update_user(user):
    db.users.update_one({"vk_id": user["vk_id"]}, {"$set": user})


def update_group(group):
    db.group.update_one({"vk_id": group["vk_id"]}, {"$set": group})


def get_users(vk_ids):
    users = []

    for vk_id in vk_ids:
        user = db.users.find_one({"vk_id": vk_id}, {"_id": 0})
        users.append(user)

    return users


def get_user(token):
    return db.users.find_one({"tokens": token}, {"_id": 0})


def post_user(token, user):
    db.users.update_one({"tokens": token}, {"$set": user})


def get_vectors(collection, ids):
    vec_arr = []

    for col_id in ids:
        vec = collection.find_one({"vk_id": col_id}, {"_id": 0, "vk_id": 1, "vector": 1, "last_update": 1, "type": 1})
        vec_arr.append(vec)

    return vec_arr


def get_user_vec(user_ids):
    return get_vectors(db.users, user_ids)


def get_group_vec(group_ids):
    return get_vectors(db.groups, group_ids)


def count(collection):
    return collection.estimated_document_count()


def users_count():
    return count(db.users)


def groups_count():
    return count(db.groups)


def init_col_cursor(collection, filters):
    cursor = collection.find(filters)
    return cursor, cursor.collection.count_documents(filters)


def init_users_cursor(filters):
    return init_col_cursor(db.users, filters)


def init_groups_cursor(filters):
    return init_col_cursor(db.groups, filters)


def get_documents(cursor, count):
    if count < 0:
        return []

    docs = []

    for i in range(count):
        if cursor.alive:
            docs.append(cursor.next())

    return docs


def is_unique_token(token):
    return db.users.find_one({"tokens": token}) is None
