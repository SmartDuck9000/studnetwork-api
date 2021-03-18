from logic import vk_interest
from analysis.interest_management.interest_tags import InterestTagManager
import db.stud_networkdb as db
import logic.graphs as graph
import analysis.interest_management.interest_metrics as metrics
import numpy as np
import pandas as pd
from logic.config import *


def merge(a, b):
    """
    function makes arr of a-size with minimal elems
    a, b - arrays
    a[i][0] is info, a[i][1] is distance (b the same)
    array a may be longer, not the opposite!"""
    ai = bi = 0
    n, nb = len(a), len(b)
    arr = [0] * n
    for i in range(n):
        if bi == nb:
            arr[i] = a[ai]
            ai += 1
        elif a[ai][1] <= b[bi][1]:
            arr[i] = a[ai]
            ai += 1
        else:
            arr[i] = b[bi]
            bi += 1
    return arr

class InterestAnalyser:
    """
    class is an interface for work with vk-analysis module with database connections.

    usage example:
        a = InterestAnalyser(path='../analysis/data')

        def form_graph(id):
            d = a.form_graph(id)
            import json
            with open('graph.json','w') as f:
                json.dump(d, f, indent=2, sort_keys=True, ensure_ascii=False)

        def add_user(id):
            a.add_user(id, speed_type='simple', verbose=False)
            a.vk_int_man.text_man.print_interest(db.get_user_vec([id])[0]['vector'])


        id = a.vk_int_man.vk_importer.load_id_by_link('https://vk.com/id1')
        add_user(id)
        form_graph(id)

    example2:
        ids = a.vk_int_man.vk_importer.load_user_ids_from_group('https://vk.com/iu7memes')
        names = []
        for id in ids:
            u = a.add_user(id, speed_type='simple', verbose=True)
    """



    def __init__(self, path):
        """path - to data folder"""
        path = path + '/'
        self.vk_int_man = vk_interest.make_vk_interest_manager(path=path)
        self.interest_tags = pd.read_csv(path+'interest_tags.csv')
        self.tag_manager = InterestTagManager(path+'tag_descriptions.csv', path+'interest_tags.csv')

    def add_user(self, vk_id, token=None, speed_type:str='simple', load_user_profile=True, verbose=True):
        """adds new user to db and returns a new user as a dict"""
        if token is not None:
            self.vk_int_man.vk_importer.set_new_token(token)
        # get vector and user info
        vector = self.vk_int_man.get_user_interest(vk_id, speed_type, verbose=verbose)
        if load_user_profile:
            d = self.vk_int_man.get_user_profile(vk_id, is_minimal=False, verbose=verbose)
        else:
            d = {'id': vk_id}
        d = self.vk_int_man.form_user_dict(d, speed_type, vector)
        d['vk_token'] = token

        # put dict into db
        db.add_user(d)
        d = db.db.users.find_one({'vk_id':d['vk_id']})
        return d

    def update_user_time(self, vk_id, verbose=True):
        """update vector with fresh info which came after last update"""
        user = db.get_user_vec(vk_id)['vector']
        token = user.get('vk_token')
        if user is None: return
        if token is not None:
            self.vk_int_man.vk_importer.set_new_token(token)

        old_vector = user['vector']
        vector = self.vk_int_man.get_user_interest(vk_id, 'quick', verbose=verbose)
        vector = self.vk_int_man.text_man.combine_vectors_weighed([[vector_weights['old_vector'], old_vector],
                                                          [vector_weights['new_vector'], vector]])

        d = self.vk_int_man.get_user_profile(vk_id, is_minimal=False)
        d = self.vk_int_man.form_user_dict(d, user['type'], vector)
        db.update_user(d)

    def upgrade_user(self, vk_id, speed_type:str='advanced', verbose=True):
        """upgrades user's load type (one of 'quick', 'simple', 'advanced'. can go only better)"""
        user = db.get_user_vec(vk_id)
        token = user.get('vk_token')
        if user is None or ((speed_type == 'simple' and user['type'] == 'quick') or
              (speed_type == 'advanced' and user['type'] == 'simple')):
            return self.add_user(vk_id, token=token, speed_type=speed_type,
                          load_user_profile=True, verbose=verbose)


    def form_graph(self, vk_id, filters=None, prev_depth=0, verbose=True):
        """form a graph (tree) for user. returned as a hierarchical dictionary"""
        if filters is None: filters = dict()
        if filters.get('tag_filter') is None:
            filters['tag_filter'] = filters
        if filters.get('search') is None:
            filters['search'] = str()

        weights = self.tag_manager.get_weight_array(filters['tag_filter'])
        search_vec = self.vk_int_man.text_man.text_to_interest(filters['search'])
        weights = weights + search_vec * interest_vector_weight
        filters.pop('tag_filter')
        filters.pop('search')

        cursor, cursor_size = db.init_users_cursor(dict())
        depth = graph.get_next_graph_depth(prev_depth)
        graph_size = graph.get_graph_size(depth) - 1  # one is for user itself

        user = db.get_user_vec([vk_id])[0]

        read_per_time = 100
        count = 0
        best = [(None, np.inf)] * graph_size
        while count < cursor_size:
            users = db.get_documents(cursor, read_per_time)
            # quick ones are 'friends' only, help-info
            users = [u for u in users if u['type'] in ['simple', 'advanced']]
            count += read_per_time
            if len(users) == 0: continue

            dists = [(us, metrics.weighed_interest_distance(user['vector'], us['vector'], weights))
                     for us in users if sum(us['vector']) != 0]
            dists.sort(key= lambda a: a[1])
            if dists[0][1] == 0:
                user = dists[0][0]
                dists = dists[1:]  # self check
            best = merge(best, dists)

        # some big-big data formatting and selection
        best = [b for b in best if b[1] != np.inf]
        best = [(user, 0)]+best  # add root
        for i in range(len(best)):
            if best[i][0].get('tokens') is not None:
                best[i][0]['token'] = best[i][0]['tokens'][0]
            best[i][0]['vk_link'] = 'vk.com/id' + str(best[i][0]['vk_id'])

        best = [{k:v for k,v in b[0].items() if k in user_card_fields_list+['vector']} for b in best]
        for i in range(len(best)):
            best[i]['tag'] = self.tag_manager.get_maximal_tag(best[i]['vector'])['description']
        user = best[0]
        best = best[1:]     # remove root

        # form graph
        graph_dict = graph.form_tree(user, best,
                                     dist_func=lambda v, w: metrics.weighed_interest_distance(v['vector'],w['vector'],
                                                                                              weights))
        graph_dict = {'depth': depth, 'graph': graph_dict}
        return graph_dict
