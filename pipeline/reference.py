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
    contents = zip(['N/A','1','2','3','4','5','6','2/3','3/4','4/5','5/6'])


@schema
class Hemisphere(dj.Lookup):
    definition = """
    hemisphere: varchar(8)
    """
    contents = zip(['left','right'])


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
    contents = zip(['lambda','bregma'])
    
    
@schema
class Device(dj.Lookup):
    definition = """ # This table contain information about the devices used for recording, or stimulation (photo or electrical). Ideally a device-type object (electrode, laser, etc.) 
    device_name: varchar(32)
    ---
    device_desc = "": varchar(1024)
    """        
    
    
@schema
class AnimalSource(dj.Lookup):
    definition = """
    animal_source: varchar(32)      # source of the animal, Jax, Charles River etc.
    """
    contents = zip(['Jackson','Homemade'])


@schema
class VirusSource(dj.Lookup):
    definition = """
    virus_source: varchar(64)
    """
    contents = zip(['UNC','UPenn','MIT','Stanford','Homemade'])


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
    contents = zip(['full','C2'])
       
    
@schema
class TrialType(dj.Lookup):
    definition = """ # # The experimental type of this trial, e.g. Lick Left vs Lick Right
    trial_type: varchar(32)
    """
    contents = zip(['lick left','lick right','N/A'])
    
    
@schema
class TrialResponse(dj.Lookup):
    definition = """ # The behavioral response of this subject of this trial - correct/incorrect with respect to the trial type
    trial_response: varchar(32)
    """
    contents = zip(['correct','incorrect','no response','early lick','N/A'])

