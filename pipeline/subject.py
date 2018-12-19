'''
Schema of subject information.
'''
import datajoint as dj
from . import reference

schema = dj.schema(dj.config.get('database.prefix', '') + 'gi2017_subject')


@schema
class Species(dj.Lookup):
    definition = """
    species: varchar(24)
    """
    contents = [['Mus musculus']]


@schema
class Strain(dj.Lookup): 
    definition = """ 
    strain: varchar(24)
    """
    contents = [['B6'],['N/A']]


@schema
class Allele(dj.Lookup):
    definition = """
    allele_name: varchar(128)
    """
    contents = [
        ['L7-cre'],
        ['rosa26-lsl-ChR2-YFP']
    ]


@schema
class Subject(dj.Manual): # temporarily remove species, strain and animalsource
    definition = """
    subject_id: varchar(64)  # id of the subject (e.g. ANM244028)
    ---
    -> Species
    -> Strain
    -> reference.AnimalSource
    sex = 'U': enum('M', 'F', 'U')
    date_of_birth = NULL: date
    subject_description=null:   varchar(1024) 
    """
    
    
@schema
class Zygosity(dj.Manual):
    definition = """
    -> Subject
    -> Allele
    ---
    zygosity:  enum('Homozygous', 'Heterozygous', 'Negative', 'Unknown')
    """

    