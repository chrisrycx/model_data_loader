'''
Classes that represent datasets used for model input and output.
'''
import os
import xarray as xr

# Load paths from environment variables
OUTPUT_PATH = os.getenv('OUTPUT_PATH', 'output')

# Model Output Dataset
class LM4ModelOutput:
    def __init__(self, site: str, forcing_string: str, version:str, spinup=False):
        '''
        Load a model output dataset.
        :param site: Site name (e.g., 'Tony Grove RS'). Can use Snotel or model name.
        :param forcing_string: Forcing string (e.g., 00000000)
        :param version: Version of the model output (e.g., 'v0.1')
        :param spinup: Whether the dataset is a spinup version
        '''
        self.site = site.replace(' ','').lower()

        # Construct the path to the output history folder
        if spinup:
            self.history_path = os.path.join(OUTPUT_PATH, self.site, f'{self.site}_spinup_{forcing_string}_{version}')
        else:
            self.history_path = os.path.join(OUTPUT_PATH, self.site, f'{self.site}_{forcing_string}_{version}')

    def get_variables(self, diag: str):

    
    def get_data(self):
        pass
    
    def close(self):
        '''
        Close the dataset to free resources.
        '''
        self.netcdf_dataset.close()