# this module contains necessary constants and restrictions for working with vk-api


# which user fields to load from vk_api
# min - minimal info needed for non-registered user
user_fields = '''sex, bdate, city, country, home_town, status,
followers_count, relatives, relation,
education, universities, schools, occupation, career, military,
movies, music, personal, quotes, tv, books, games, interests,
photo_400_orig
'''
min_user_fields = '''sex'''

user_fields_list = user_fields.split(', ')
min_user_fields_list = min_user_fields.split(', ')


# which group fields to load from vk_api
group_fields = '''city, country, place, description, wiki_page, members_count, counters, start_date,
 finish_date, can_post, can_see_all_posts, activity, status, contacts, links, fixed_post, 
 verified, site, can_create_topic'''

group_fields_list = group_fields.split(', ')


# which post fields to load from vk_api
post_fields = '''id, date, text, comments, likes, reposts'''

post_fields_list = post_fields.split(', ')


# vk-api limits
max_get_members_read_per_time = 1000
max_wall_read_per_time = 100
max_newsfeed_read_per_time = 100