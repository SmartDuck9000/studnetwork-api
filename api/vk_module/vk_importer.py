import pandas as pd
import re
import vk

from vk_module.vk_constants import *


def load_default_token():
    """if no token is set from outside, attempt will be taken to load
    some preset tokens from a certain module"""
    try:
        from .vk_tokens import super_secret_access_token
        return super_secret_access_token
    except:
        return None


def create_session(func):
    """uses token to create a vk_api connection.
    decorates load-functions to omit token-work
    also used for a delayed session creation (gives time to set needed tokens)"""
    def decorated(c, *args, **kwargs):
        if c.vk_api is None:
            if c.token is None:
                c.token = load_default_token()
                if c.token is None:
                    raise Exception('no token found to make a vk-session!')
            session = vk.Session(access_token=c.token)
            c.vk_api = vk.API(session, v="5.92")

        return func(c, *args, **kwargs)
    return decorated


def session_manager(cls):
    """applies 'create_session' decorator for all methods in class starting with 'load'"""
    callable_attributes = {k:v for k, v in cls.__dict__.items()
                           if callable(v) if k.startswith('load')}

    for name, func in callable_attributes.items():
        decorated = create_session(func)
        setattr(cls, name, decorated)
    return cls


@session_manager
class VkImporter:
    """class is used to load data using vk-api
    access to vk_api is granted using vk tokens"""

    def __init__(self, auth_token = None):
        self.set_new_token(auth_token)
        self.vk_api = None

    def set_new_token(self, token):
        self.token = token

    def load_user_ids_from_group(self, group_id, cnt: int = -1):
        """returns array of ids for members of given group (loads all ids if 'cnt'=-1, else 'cnt')
        group is either integer or a str: link to the group"""
        if isinstance(group_id, str):
            group_id = self.load_id_by_link(group_id)
        total_members = self.vk_api.groups.getMembers(group_id=group_id, count=0)['count']
        to_read = min(total_members, cnt if cnt > 0 else total_members)

        user_ids = self._cycle_vk_read(max_get_members_read_per_time, to_read,
                                       self.vk_api.groups.getMembers, group_id=group_id)
        return user_ids

    def load_id_by_link(self, link: str):
        """define id of vk-instance using its link (possible use for: groups, users etc.)"""
        id = link
        if 'vk.com/' in link:
            id = link.split('/')[-1]
            if not re.sub('id|club', '', id).isdigit():
                resp = self.vk_api.utils.resolveScreenName(screen_name=id)
                if len(resp) == 0: return None
                id = resp['object_id']
            else:
                id = re.sub('id|club', '', id)
        return int(id)

    def load_user_data(self, user_ids, fields: str = user_fields,
                       get_groups=True, get_friends=True,
                       load_photos_cnt: int = 0):
        """loads info about given users.
        'fields' format: str, values comma-separated, e.g.: 'first_name, last_name'
        returns pd.Dataframe object, columns are fields, rows - users"""
        user_data = self.vk_api.users.get(user_ids=user_ids, fields=fields)

        for i, id in enumerate(user_ids):
            if load_photos_cnt > 0:
                photos = self.vk_api.photos.getAll(owner_id=id, count=load_photos_cnt)
                if photos['count'] != 0:
                    user_data[i]['photos'] = [p['sizes'][-1]['url'] for p in photos['items']]
            try:
                if get_groups:  user_data[i]['groups'] = self.vk_api.groups.get(user_id=id)['items']
                if get_friends: user_data[i]['friends'] = self.vk_api.friends.get(user_id=id)['items']
            except:
                if get_groups: user_data[i]['groups'] = [None]
                if get_friends: user_data[i]['friends'] = [None]

        user_df = pd.DataFrame(user_data)
        return user_df

    def load_posts(self, owner_id: int, count=100, is_group=False):
        """loads posts on the wall of group or user.
        if group, you must either set flag 'is_group' or send negative id"""
        owner_id *= -1 if is_group else 1
        try:
            posts = self._cycle_vk_read(max_wall_read_per_time, count,
                                        self.vk_api.wall.get, owner_id=owner_id)

        except Exception as ex:
            print(ex)
            return None
        if len(posts) == 0: return None
        posts = pd.DataFrame(posts)
        return posts[post_fields_list]

    def _cycle_vk_read(self, read_per_time, total_read, func, *args, **kwargs):
        """repeatedly reads values from limited load-speed vk-functions (e.g. 'wall.get')
        forms an array from 'items' filed got from func, then returns summarized array"""
        values = []
        offset = 0
        while offset < total_read:
            values += func(*args, **kwargs, count=read_per_time, offset=offset)["items"]
            offset += read_per_time
        return values