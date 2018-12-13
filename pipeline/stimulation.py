'''
Schema of stimulation information.
'''
import re
import os
from datetime import datetime
import numpy as np
import scipy.io as sio
import datajoint as dj
from . import reference

schema = dj.schema('ttngu207_stimulation',locals())

@schema
class PhotoStimType(dj.Lookup):
   definition = """
   photo_stim_id: varchar(8)
   ---
   -> reference.BrainLocation
   -> reference.Hemisphere
   photo_stim_period:                  varchar(24)  # period during the trial
   photo_stim_relative_location:       varchar(24)  # stimulus location relative to the recording.
   photo_stim_act_type:                varchar(24)  # excitation or inihibition
   photo_stim_duration:                float        # in ms, stimulus duration
   photo_stim_shape:                   varchar(24)  # shape of photostim, cosine or pulsive
   photo_stim_freq:                    float        # in Hz, frequency of photostimulation
   photo_stim_notes='':                varchar(128)
   """
#   contents = [
#       ['0', '', 'N/A', 'N/A', '', '', '', '', 0, '', 0, 'no stimulus'],
#       ['1', 'Fastigial', 'N/A', 'N/A', 'right', 'sample', 'contralateral', 'activation', 500, '5ms pulse', 20, ''],
#       ['2', 'Fastigial', 'N/A', 'N/A', 'right', 'delay', 'contralateral', 'activation', 500, '5ms pulse', 20, ''],
#       ['3', 'Dentate', 'N/A', 'N/A', 'right', 'sample', 'contralateral', 'activation', 500, '5ms pulse', 20, ''],
#       ['4', 'Dentate', 'N/A', 'N/A', 'right', 'delay', 'contralateral', 'activation', 500, '5ms pulse', 20, ''],
#       ['5', 'DCN', 'right', 'N/A', 'N/A', 'delay', 'contralateral', 'inhibition', 500, 'cosine', 40, ''],
#       ['6', 'DCN', 'right', 'N/A', 'N/A', 'delay', 'contralateral', 'inhibition', 500, 'cosine', 40, ''],
#       ['NaN','', 'N/A', 'N/A', '', '', '', '', 0, '', 0, 'stimulation configuration for other purposes, should not analyze']
#   ]