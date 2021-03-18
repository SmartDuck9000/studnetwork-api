from progress.bar import IncrementalBar
from vk_module.vk_importer import VkImporter
from vk_module.vk_constants import *

import db.stud_networkdb as db

from analysis.interest_management.text_interest import TextInterestManager
from analysis.data_parsing.word_vectorizer import WordVectorizer
from common.timestamp import *
from .config import *


def extract_field(d, field, extract_value):
    """save feature extraction from dict"""
    if d.get(field) is not None:
        d[field] = d[field][extract_value]


def pop_field(d, field):
    """save dict-field deletion: no exceptions"""
    if d.get(field) is not None:
        d.pop(field)


def make_vk_interest_manager(path='data', vectorizer='model.bin', csv='interest_groups.csv'):
    """creates a VkInterestManager based on model files locations, not working managers.
    used for more quick and simple creation of instances"""

    wv = WordVectorizer(path+'/'+vectorizer)
    trans = TextInterestManager(path+'/'+csv, wv)
    man = VkInterestManager(VkImporter(), trans)
    return man


class VkInterestManager():
    """class is used to define interest vectors for vk-instances like posts, groups and users.
    uses db in order to effective definition of friends' and groups' interests while
    defining so for user

    methods with names like 'get_***_interest' and '***_analysis' return interest vector
    """

    def __init__(self, vk_imp: VkImporter, text_man: TextInterestManager):
        self.vk_importer = vk_imp
        self.text_man = text_man


    def get_post_interest(self, post):
        """post is a dict loaded from vk-api"""
        return self.text_man.text_to_interest(post['text'])


    def get_group_interest(self, group, verbose=True):
        """group is either id (positive one) or a str-link"""
        if isinstance(group, str):
            group_id = self.vk_importer.load_id_by_link(group)
            if group_id is None:
                return self.text_man.make_zeros()
        else: group_id = group

        if verbose: print('defining group id', group_id, 'interests:\n    loading posts...')
        posts = self.vk_importer.load_posts(group_id, count=group_post_count_analysis, is_group=True)
        if posts is None: return self.text_man.make_zeros()

        if verbose: bar = IncrementalBar('    parsing posts', max=len(posts['text']))
        vectors = []
        for _, p in posts.iterrows():
            vectors += [self.get_post_interest(p)]
            if verbose: bar.next()

        if verbose: bar.finish()
        return self.text_man.combine_vectors(vectors)


    def get_user_profile(self, vk_id, is_minimal=True, verbose=True):
        """loads either minimal info or full one for profile"""
        if verbose: print('loading user', vk_id, 'profile....')
        fields = min_user_fields if is_minimal else user_fields
        user_df = self.vk_importer.load_user_data([vk_id], fields=fields,
                                                  get_groups=False, get_friends=False)

        # no error if column missing: checked
        user_df = user_df.rename(columns={'id': 'vk_id', 'photo_400_orig': 'avatar_photo'})

        d = user_df.T.to_dict()[0]
        extract_field(d, 'city', 'title')
        extract_field(d, 'country', 'title')
        extract_field(d, 'occupation', 'name')

        pop_field(d, 'is_closed')
        pop_field(d, 'can_access_closed')
        return d


    def form_user_dict(self, user_dict, speed_type, vector):
        user_dict['last_update'] = get_cur_timestamp()
        user_dict['type'] = speed_type
        user_dict['vector'] = list(vector)
        return user_dict


    def get_user_interest(self, user, speed_type:str = 'simple', verbose=True):
        """user is either id (positive one) or a str-link
        speed_type is one of the following:
          - 'quick': analyse only user's info (wall, interest field)
          - 'simple': analyse all (user's info, groups, friends), but if data not present in db,
              it is omitted
          - 'advanced': analyse all, update db with missing info about friends (using 'quick') and groups."""

        if isinstance(user, str):
            user_id = self.vk_importer.load_id_by_link(user)
            if user_id is None:
                return self.text_man.make_zeros()
        else: user_id = user

        if verbose: print('defining user', user_id, 'interests (', speed_type, '):')
        load_advanced = (speed_type in ['simple', 'advanced'])
        user_data = self.vk_importer.load_user_data([user_id], fields='',
                                                    get_friends=load_advanced, get_groups=load_advanced).iloc[0]

        analyse_vectors = [self._user_wall_analysis(user_id, verbose=verbose),
                           self._user_interest_analysis(user_id, verbose=verbose)]
        if load_advanced:
            analyse_vectors.append(self._friends_analysis(user_data['friends'], speed_type, verbose=verbose))
            analyse_vectors.append(self._groups_analysis(user_data['groups'], speed_type, verbose=verbose))

        analyse_vectors = [x for x in analyse_vectors if x[0] is not None and x[1] is not None]

        if len(analyse_vectors) > 1:
            return self.text_man.combine_vectors_weighed(analyse_vectors)
        elif len(analyse_vectors) == 1:
            return analyse_vectors[0][1]    # 0 is weight, 1 is vector itself. so, return vector from vecs[0]
        else: return self.text_man.make_zeros()


    def _user_wall_analysis(self, user_id, verbose=True):
        """analyse user's wall"""
        if verbose: print("    parsing user's wall...\n        loading posts...")
        wall_posts = self.vk_importer.load_posts(user_id, count=user_post_count_analysis, is_group=False)

        if wall_posts is not None:
            if verbose: bar = IncrementalBar('        parsing posts', max=len(wall_posts['text']))
            vectors = []
            for _, p in wall_posts.iterrows():
                vectors += [self.get_post_interest(p)]
                if verbose: bar.next()

            if verbose: bar.finish()
            wall_vector = self.text_man.combine_vectors(vectors)
            return vector_weights['user_wall'], wall_vector
        else: return None, None


    def _user_interest_analysis(self, user_id, verbose=True):
        # analyse user's field 'my interests'
        if verbose: print("    reading user's interests...")
        user_data = self.vk_importer.load_user_data([user_id], fields='interests',
                                                    get_friends=False, get_groups=False).iloc[0]

        if user_data.get('interests') is not None:
            interest_vector = self.text_man.text_to_interest(user_data['interests'])
            return vector_weights['user_interests'], interest_vector
        else: return None, None


    def _groups_analysis(self, groups, speed_type: str, verbose=True):
        # analyse user's groups
        if speed_type in ['simple', 'advanced']:
            if verbose: print("    analysing user's groups")
            db_found = calculated = 0
            raw_vectors = db.get_group_vec(groups)

            group_vectors = []
            size = len(groups)
            for i, (g, vec) in enumerate(zip(groups, raw_vectors)):
                if verbose: print('group:', i, '/', size, end=': ')
                if g is None:
                    if verbose: print('no access')
                    continue

                if vec is not None:
                    group_vectors.append(vec['vector'])
                    db_found += 1
                    if verbose: print('        group found in db!')
                    continue
                elif speed_type is 'advanced' and calculated < max_advanced_group_load:
                    vec = self.get_group_interest(g)
                    group_vectors.append(vec)
                    db.add_group({'vk_id':g, 'vector':list(vec), 'last_update': get_cur_timestamp()})
                    calculated += 1

                if verbose: print()

            if verbose: print("        groups found in db:", db_found)
            if verbose: print("        groups calculated:", calculated)

            return  vector_weights['groups'], self.text_man.combine_vectors(group_vectors)
        else: return None, None

    def _friends_analysis(self, friends, speed_type: str, verbose=True):
        # analyse user's friends
        if speed_type in ['simple', 'advanced']:
            if verbose: print("    analysing user's friends")
            db_found = calculated = 0
            raw_vectors = db.get_user_vec(friends)

            friend_vectors = []
            size = len(friends)
            for i, (id, vec) in enumerate(zip(friends, raw_vectors)):
                if verbose: print('user:', i, '/', size, end=': ')
                if id is None:
                    if verbose: print('no access')
                    continue

                if vec is not None:
                    friend_vectors.append(vec['vector'])
                    db_found += 1
                    if verbose: print('        user found in db!')
                    continue
                elif speed_type is 'advanced' and calculated < max_advanced_friend_load:
                    vec = self.get_user_interest(id, speed_type='quick')
                    d = self.get_user_profile(id, is_minimal=True)
                    d = self.form_user_dict(d, 'quick', vec)
                    friend_vectors.append(vec)
                    db.add_user(d)
                    calculated += 1

                if verbose: print()

            if verbose: print("        friends found in db:", db_found)
            if verbose: print("        friends quick calculated:", calculated)

            return vector_weights['friends'], self.text_man.combine_vectors(friend_vectors)
        else: return None, None


if __name__ == '__main__':
    man = make_vk_interest_manager(path='../data')

    it = man.get_group_interest('https://vk.com/itcookies')
    man.text_man.print_interest(it)
