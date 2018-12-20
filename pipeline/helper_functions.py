import os
from datetime import datetime

import h5py as h5

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


def find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment):
        ############## Dataset #################
        sess_data_files = os.listdir(sess_data_dir)
                        
        # Search the filenames to find a match for "this" session (based on key)
        sess_data_file = None
        for s in sess_data_files:
            try:
                temp_nwb = h5.File(os.path.join(sess_data_dir,s), 'r')
            except:
                print(f'!!! error load file: {s}')   
                continue
            # read subject_id out of this file
            subject_id = temp_nwb['general']['subject']['subject_id'].value.decode('UTF-8')
            # -- session_time 
            session_start_time = temp_nwb['session_start_time'].value
            session_start_time = parse_prefix(session_start_time)
            # compare key with extracted info from this file
            if (animal_id == subject_id) and (date_of_experiment == session_start_time):
                # if true, meaning the current "nwb" variable is a match with this session
                sess_data_file = s
                break
            temp_nwb.close()
                    
        # If session not found from dataset, break
        if sess_data_file is None:
            print(f'Session not found! - Subject: {animal_id} - Date: {date_of_experiment}')
            return None
        else: 
            print(f'Found datafile: {sess_data_file}')
            return sess_data_file
        
        