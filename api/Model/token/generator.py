import db.stud_networkdb as db
import secrets


def generate_token(vk_id):
    unique_flag = False
    token = None

    while not unique_flag:
        token = secrets.token_hex()
        unique_flag = db.is_unique_token(token)

    return token
