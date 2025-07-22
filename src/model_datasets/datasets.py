'''
Classes that represent datasets used for model input and output.
'''
import os
import pandas as pd
import xarray as xr

# Load paths from environment variables
OUTPUT_PATH = os.getenv('OUTPUT_PATH', None)
if OUTPUT_PATH is None:
    raise ValueError("OUTPUT_PATH environment variable is not set. Please set it to the model output directory.")

# Model Output Dataset
class LM4ModelOutput:
    def __init__(self, site: str, forcing_string: str, version:str, spinup=False):
        '''
        Load a model output dataset.
        :param site: Site name (e.g., 'Tony Grove RS'). Can use Snotel or model name.
        :param forcing_string: Forcing string (e.g., 00000000)
        :param version: Version of the model output (e.g., '0.1')
        :param spinup: Whether the dataset is a spinup version
        '''
        self.site = site.replace(' ','').lower()

        # Construct the path to the output history folder
        if spinup:
            self.history_path = os.path.join(OUTPUT_PATH, self.site, f'{self.site}_spinup_s{forcing_string}_v{version}','history')
        else:
            self.history_path = os.path.join(OUTPUT_PATH, self.site, f'{self.site}_s{forcing_string}_v{version}','history')

        # Initialize dictionary to hold diagnostic datasets
        self.diagnostics = {}

    def load_diagnostic(self, diag: str):
        '''
        Load a diagnostic dataset.
        :param diag: Diagnostic name (e.g., 'land_daily')
        :return: xarray Dataset for the diagnostic
        '''
        if diag not in self.diagnostics:
            # Construct the path to the diagnostic file. File name will have the format 'XXXX.diag.nc' where XXXX is the start date.
            # First find the file name in the history path
            diag_file = next((f for f in os.listdir(self.history_path) if f.endswith(f'{diag}.nc')), None)
            if not diag_file:
                raise FileNotFoundError(f'Diagnostic file {diag} does not exist.')

            # Load the dataset using xarray
            self.diagnostics[diag] = xr.open_dataset(os.path.join(self.history_path, diag_file), decode_timedelta=False)

        return self.diagnostics[diag]
    
    def get_variables(self, diag: str) -> pd.DataFrame:
        '''
        Returns a dataframe with the variables in the diagnostic dataset.
        '''
        diagnostic = self.load_diagnostic(diag)

        vars_df = pd.DataFrame({
            'dimensions': [diagnostic[var].dims for var in diagnostic.data_vars],
            'long_name': [diagnostic[var].attrs.get('long_name', '') for var in diagnostic.data_vars],
            'units': [diagnostic[var].attrs.get('units', '') for var in diagnostic.data_vars]
        }, index=diagnostic.data_vars)

        return vars_df
    
    def get_data(self, vars: list[str], diag: str) -> pd.DataFrame:
        '''
        Get data for specified variables in a diagnostic dataset. This always returns a DataFrame, even if only one variable is requested.
        Variables associated with multiple depths (soil) will be returned as separate columns.
        :param vars: List of variable names to retrieve
        :param diag: Diagnostic name (e.g., 'land_daily')
        :return: DataFrame with the requested variables

        Note: This method will need to be improved over time to handle different types of data.
        '''
        diagnostic = self.load_diagnostic(diag)

        # Verify that all requested variables exist not soil related, this will be improved later
        for var in vars:
            if var.startswith('soil_'):
                # Additional handling for soil-related variables can be added here
                ValueError(f"Variable '{var}' is not yet supported in this method. Please use get_variables() to explore available variables.")

        data = diagnostic[vars].isel(grid_index=0).to_dataframe()

        # For daily datasets, change index to be gregorian dates, this will only have a minor affect on spinup data
        if diag == 'land_daily':
            # Get the first time coordinate from the daily dataset
            model_start_str = diagnostic['time'].to_index()[0].strftime('%Y-%m-%d 12:00')
            model_end_str = diagnostic['time'].to_index()[-1].strftime('%Y-%m-%d 12:00')
            model_start = pd.Timestamp(model_start_str)

            # Create a date range for the model index
            # Adjust the end date to account for the leap year in 1900
            if model_start < pd.Timestamp('1900-03-01'):
                model_end = pd.Timestamp(model_end_str) + pd.Timedelta(days=1)  # Add on a day to account for the leap year in 1900
            else:
                model_end = pd.Timestamp(model_end_str) 

            data.index = pd.date_range(start=model_start, end=model_end, freq='D')
        else:
            data.index = pd.to_datetime(data.index) #This will give a warning but it won't matter for monthly data

        return data
    
    def close(self):
        '''
        Close any open diagnostic datasets.
        '''
        for diag in self.diagnostics.values():
            diag.close()