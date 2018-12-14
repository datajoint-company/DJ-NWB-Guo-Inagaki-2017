import numpy as np
from datetime import datetime
from . import reference
# datetime format - should probably read this from a config file and not hard coded here
datetimeformat_ymd = '%y%m%d'
datetimeformat_ydm = '%y%d%m'
datetimeformat_ymdhms = '%Y-%m-%d %H:%M:%S'

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

def parse_prefix(line):
    cover = len(datetime.now().strftime(datetimeformat_ymdhms))
    return datetime.strptime(line[:cover], datetimeformat_ymdhms)

#def EncodeTrialType(trial_type_list):
#    # Get trial type from db and map to dict
#    trial_types = reference.TrialType.fetch()
#    trial_type_keys = {}
#    for tr in trial_types:
#        trial_type_keys[tr[0]] = tr[1]
#    # Read applicable trial type from input and form a on/off 0/1 array
#    key_array = np.zeros((len(trial_type_keys)))
#    for t in trial_type_list:
#        key_array[trial_type_keys[t]] = 1
#    # Convert to a string
#    trial_type_str_array = ''
#    for k in key_array:
#        trial_type_str_array += str(int(k))
#    return trial_type_str_array
#    
#def DecodeTrialType(trial_type_str_array):
#    # Get trial type from db and map to dict
#    trial_types = reference.TrialType.fetch()
#    trial_type_keys = {}
#    for tr in trial_types:
#        trial_type_keys[str(tr[1])] = tr[0]
#    # Read 0/1 code from input and decode to trial type
#    trial_type_list = []
#    for idx, v in enumerate(trial_type_str_array):
#        if v == '1':
#            trial_type_list.append(trial_type_keys[str(idx)])
#    return trial_type_list









