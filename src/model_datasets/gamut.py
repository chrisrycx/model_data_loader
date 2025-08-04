'''
A class for managing the Gamut dataset.
'''

import os
import pandas as pd

GAMUT_PATH = os.getenv('GAMUT_PATH')
if GAMUT_PATH is None:
    raise ValueError("GAMUT_PATH environment variable is not set.")

GAMUT_PATH = str(GAMUT_PATH)

# Mapping of site names to abbreviations, will add as needed
site_abbrev = {'Tony Grove': 'TG'}

class GamutDataset:
    def __init__(self, site: str):
        '''
        Initialize the GamutDataset class.
        :param site: Site name (e.g., 'Tony Grove'). Use GAMUT name: https://uwrl.usu.edu/lro/locations.
        '''
        self.site = site
        self.site_dir_name = self.site.lower().replace(' ', '')

    def find_files(self) -> list[str]:
        '''
        Find all the files in the GAMUT directory for the specified site.
        Corresponding files follow the convention: 'LR_{site_abbrev}_C_...}
        :return: List of file names.
        '''
        site_files = []
        site_dir = os.path.join(GAMUT_PATH, self.site_dir_name)
        for file in os.listdir(site_dir):
            if file.startswith(f'LR_{site_abbrev[self.site]}_C') and file.endswith('.csv'):
                site_files.append(file)
        
        return site_files
    
    def load_csv(self, file_name: str) -> pd.DataFrame:
        '''
        Load a CSV file from the GAMUT dataset.
        :param file_name: Name of the CSV file to load.
        :return: DataFrame containing the data from the CSV file.
        '''
        file_path = os.path.join(GAMUT_PATH, self.site_dir_name, file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_name} does not exist in {self.site} directory.")
        
        # Determine how many rows to skip by searching for header row
        with open(file_path, 'r') as f:
            for i, line in enumerate(f):
                if 'LocalDateTime' in line:
                    header_row = i
                    break
            else:
                raise ValueError("Header row not found.")

        df = pd.read_csv(file_path, skiprows=header_row, parse_dates=['LocalDateTime'], index_col='LocalDateTime')
        return df
    
    def get_variables(self) -> list[str]:
        '''
        Get a list of variables from the specified files.
        Variables follow the convention: 'LR_{site_abbrev}_C_{variable_name}_SourceID...'
        :param filenames: List of file names to extract variables from.
        :return: List of unique variable names.
        '''
        filenames = self.find_files()

        variables = []
        site_id = f'LR_{site_abbrev[self.site]}_C_'
        file_meta = 'SourceID_1_QC_1.csv'
        for filename in filenames:
            print(f"Processing file: {filename}")
            if filename.startswith(site_id) and filename.endswith(file_meta):
                variable_name = filename[len(site_id):-len(file_meta)-1]
                variables.append(variable_name)

        return list(set(variables))
    
    def get_data(self, variable: str) -> pd.Series:
        '''
        Get data for a specific variable from the GAMUT dataset.
        :param variable: Variable name to retrieve data for.
        :return: DataFrame containing the data for the specified variable in UTC.
        '''
        file_name = f'LR_{site_abbrev[self.site]}_C_{variable}_SourceID_1_QC_1.csv'
        file_path = os.path.join(GAMUT_PATH, self.site_dir_name, file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_name} does not exist in {self.site} directory.")
        
        rawdf = self.load_csv(file_name)

        # Extract just the relevant columns
        data = rawdf[variable]

        # All GAMUT data has a constant offset of 7 from UTC
        data.index = data.index + pd.Timedelta(hours=7)

        return data
