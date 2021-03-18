import datetime
import time

def get_cur_timestamp():
    """returns current data in unix time format"""
    return int(time.mktime(datetime.datetime.now().timetuple()))