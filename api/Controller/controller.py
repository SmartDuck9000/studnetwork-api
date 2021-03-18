from Model.Auth import VkAuth
import Model.token.generator as tg

import Controller.config as config
import db.stud_networkdb as db
import logic.analyser as analise

analyser = analise.InterestAnalyser("analysis/data")

# code: access code, that vk returns after auth
# returns user token, that identifies user device
# user token stored in users doc in array
def login(code):
    vk_id, vk_token = VkAuth.login(code)
    user = analyser.add_user(vk_id, vk_token)
    token = tg.generate_token(vk_id)

    if user.get('tokens') is None:
        user['tokens'] = []
    user['tokens'].append(token)

    db.update_user(user)
    print(token)
    return token


# token: user token in string format, that identifies user device
# returns user in dict format from db
def get_user(token):
    user = db.get_user(token)
    keys = config.secure_fields
    user = {k: v for k, v in user.items() if k not in keys}
    return user


# updates user in db
# token: user token in string format, that identifies user device
# user: dict, that contains new user data
def post_user(token, user):
    db.post_user(token, user)


# deletes user token from db
# token: user token in string format, that identifies user device
# returns status code
def exit_user(token):
    user = db.get_user(token)
    if user is None:
        return 401

    user['tokens'].remove(token)

    return 200


# returns graph of users intersts
# token: user token in string format, that identifies user device
# filters: dict, that contains info about filter parameters
# depth: depth of graph
def get_graph(token, filters, depth):
    user = db.get_user(token)
    vk_id = user['vk_id']
    return analyser.form_graph(vk_id, filters=filters, prev_depth=depth)
