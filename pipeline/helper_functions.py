import numpy as np
from datetime import datetime

# datetime format - should probably read this from a config file and not hard coded here
datetimeformat_ymd = '%y%m%d'
datetimeformat_ydm = '%y%d%m'

time_unit_convert_factor = {
        'millisecond': 10e-3,
        'second':1,
        'minute':60,
        'hour':3600,
        'day':86400                
        }

def get_one_from_nested_array(nestedArray):
    if nestedArray.size == 0: return None
    unpackedVal = nestedArray
    while unpackedVal.shape != (): 
        if unpackedVal.size == 0: return None
        unpackedVal = unpackedVal[0]
    return unpackedVal

def get_list_from_nested_array(nestedArray):
    if nestedArray.size == 0: return None
    unpackedVal = nestedArray
    l = []
    if unpackedVal.size == 0: return None
    for j in np.arange(unpackedVal.size):
        tmp = unpackedVal.item(j)
        try: tmp = get_one_from_nested_array(tmp)
        except: pass
        l.append(tmp)            
    return l    

def extract_datetime(datetime_str):
    if datetime_str is None : 
        return None
    else: 
        try: 
            # expected datetime format: yymmdd
            return datetime.strptime(str(datetime_str),datetimeformat_ymd) 
        except:
            # in case some dataset has messed up format: yyddmm
            try:
                return datetime.strptime(str(datetime_str),datetimeformat_ydm) 
            except: 
                print(f'Session Date error at {datetime_str}') # let's hope this doesn't happen
                return None
