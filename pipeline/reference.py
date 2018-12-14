'''
Schema of subject information.
'''
import datajoint as dj

schema = dj.schema(dj.config.get('database.prefix', '') + 'gi2017_reference')

@schema
class CorticalLayer(dj.Lookup):
    definition = """
    cortical_layer : varchar(8) # layer within cortex
    """
    contents = [['N/A'],['1'],['2'],['3'],['4'],['5'],['6'],['2/3'],['3/4'],['4/5'],['5/6']]

@schema
class Hemisphere(dj.Lookup):
    definition = """
    hemisphere: varchar(8)
    """
    contents = [['left'], ['right']]

@schema
class BrainLocation(dj.Manual): # "dj.Manual" here because, for different session in a dataset, or across different dataset, most likely new applicable brain location will be entered. Unless we have some giant atlas/templates with all brain locations (very unlikely)
    definition = """ 
    brain_region: varchar(32)
    brain_subregion = 'N/A' : varchar(32)
    -> CorticalLayer
    -> Hemisphere
    ---
    brain_location_full_name = 'N/A' : varchar(128)
    """
#    contents = [
#        {'brain_location':'N/A','brain_location_full_name':'N/A','cortical_layer': 'N/A', 'brain_subregion':'N/A'},
#        {'brain_location':'fastigial','brain_location_full_name':'cerebellar fastigial nucleus','cortical_layer': 'N/A', 'brain_subregion':'N/A'},
#        {'brain_location':'alm','brain_location_full_name':'anteriror lateral motor cortex','cortical_layer': 'N/A', 'brain_subregion':'N/A'},
#        {'brain_location':'barrel','brain_location_full_name':'N/A','cortical_layer': '4', 'brain_subregion':'c2'},
#        {'brain_location':'vm/val','brain_location_full_name':'ventral medial/ventral anterior-lateral','cortical_layer': 'N/A', 'brain_subregion':'N/A'},
#        {'brain_location':'trn','brain_location_full_name':'thalamic reticular nucleus','cortical_layer': 'N/A', 'brain_subregion':'N/A'}
#    ]

@schema
class CoordinateReference(dj.Lookup):
    definition = """
    coordinate_ref: varchar(32)
    """
    contents = [['lambda'], ['bregma']]
    
@schema
class Device(dj.Lookup):
    definition = """ # ideally a device-type object (electrode, laser, etc.) 
    device_name: varchar(32)
    ---
    device_desc = "": varchar(1024)
    """        
    
@schema
class AnimalSource(dj.Lookup):
    definition = """
    animal_source: varchar(32)      # source of the animal, Jax, Charles River etc.
    """
    contents = [['Jackson'], ['Homemade']]

@schema
class VirusSource(dj.Lookup):
    definition = """
    virus_source: varchar(64)
    """
    contents = [['UNC'], ['UPenn'], ['MIT'], ['Stanford'], ['Homemade']]

@schema
class ProbeSource(dj.Lookup):
    definition = """
    probe_source: varchar(64)
    ---
    number_of_channels: int
    """
    contents = [
        ['Cambridge NeuroTech', 64],
        ['NeuroNexus', 32]
    ]

@schema
class Virus(dj.Lookup):
    definition = """
    virus: varchar(64) # name of the virus
    ---
    -> VirusSource
    virus_lot_number="":  varchar(128)  # lot numnber of the virus
    virus_titer=null:       float     # x10^12GC/mL
    """
#    contents = [
#        {'virus_name': 'AAV2-hSyn-hChR2(H134R)-EYFP', 
#         'virus_source_name': 'UNC'
#        }
#    ]

@schema
class Experimenter(dj.Lookup):
    definition = """
    experimenter: varchar(64)
    """
    contents = [['Nuo Li']]

@schema
class WhiskerConfig(dj.Lookup):
    definition = """
    whisker_config: varchar(32)
    """
    contents = [['full'], ['C2']]
       
@schema
class TrialType(dj.Lookup):
    definition = """ # An internal lookup table to encode/decode multiple trial-type labels describing a particular trial (e.g. a trial can be 'No Stim', 'Lick L trial' and 'Incorrect L')
    trial_type: varchar(64)
    ---
    trial_type_code: int
    """
    contents = [
            ['No Stim',0],
            ['Stim',1],
            ['Lick R trial',2],
            ['Lick L trial',3],
            ['Stim trials',4],
            ['No response',5],
            ['Early lick',6],
            ['Incorrect L',7],
            ['Incorrect R',8],
            ['Correct L',9],
            ['Correct R',10]
            ]  
    
@schema
class BehavioralType(dj.Lookup):
    definition = """
    behavior_acquisition_type: varchar(64)
    """    
    contents = [
            ['thetaAtBase'],
            ['ampitude'],
            ['phase'],
            ['setpoint'],
            ['thetafilt'],
            ['deltaKappa'],
            ['touch_onset'],
            ['touch_offset'],
            ['distance_to_pole'],
            ['pole_available'],
            ['beam_break_times']
            ]
    
@schema
class ExtracellularType(dj.Lookup):
    definition = """
    extracellular_acquisition_type: varchar(64)
    """    
    contents = [
            ['voltage'],
            ['spike']
            ]   

@schema
class IntracellularType(dj.Lookup):
    definition = """
    intracellular_acquisition_type: varchar(64)
    """    
    contents = [
            ['membrane_potential'],
            ['membrane_potential_wo_spike']
            ]      

    
    
    
    