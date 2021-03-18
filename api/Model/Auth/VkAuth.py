import data.app_data as ad
import Model.Auth.data as data
import requests


def login(access_code):
    url = get_url(access_code)
    json = requests.get(url).json()

    return json['user_id'], json['access_token']

def get_url(access_code):
    url = data.oauth + ad.app_id \
          + data.client_secret + ad.app_secure_code \
          + data.redirect_uri \
          + data.code + access_code

    return url
