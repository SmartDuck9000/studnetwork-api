# graph configs
expand_sizes = [4, 3, 3, 2, 2]
later_expand_size = 1
start_depth = 8
depth_step = 4


# which fields return as user cards
user_card_fields = '''first_name, last_name, sex, bdate, city, country, 
avatar_photo, photos, purpose, interests, token, vk_link'''

user_card_fields_list = user_card_fields.replace('\n', ' ').split(', ')

# loading limits
max_advanced_group_load = 32
max_advanced_friend_load = 32
load_user_photos_cnt=3
graph_group_weight=50

# how many posts are used to analyse one's wall
group_post_count_analysis = 100
user_post_count_analysis = 100

# weights
interest_vector_weight = 4
vector_weights = {'user_wall': 3, 'user_interests': 10,
                  'friends': 1, 'groups': 1,
                  'old_vector':1, 'new_vector':2}


