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
            self.history_path = os.path.join(OUTPUT_PATH, self.site, f'{self.site}_spinup_v{version}','history')
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
    
    def get_gregorian_index(self, diag: str) -> pd.DatetimeIndex:
        '''
        Generate a gregorian date index for the model output.
        This really only matters for the daily datasets, but it will return the index for any diagnostic.
        :param diag: Diagnostic name (e.g., 'land_daily')
        :return: pd.DatetimeIndex for the model output
        '''
        # Error if the diagnostic is not supported
        if diag not in ['land_daily', 'land_month']:
            raise ValueError(f"Diagnostic '{diag}' is not supported. Please use 'land_daily' or 'land_month'.")
        
        # For land_month, can use method on existing diagnostic
        if diag == 'land_month':
            land_month = self.load_diagnostic('land_month')
            return land_month['time'].to_index().to_datetimeindex()

        # Else land_daily
        # Get the first time coordinate from the daily dataset
        land_daily = self.load_diagnostic('land_daily')
        model_start_str = land_daily['time'].to_index()[0].strftime('%Y-%m-%d 12:00')
        model_end_str = land_daily['time'].to_index()[-1].strftime('%Y-%m-%d 12:00')
        model_start = pd.Timestamp(model_start_str)

        # Create a date range for the model index
        # Adjust the end date to account for the leap year in 1900
        if model_start < pd.Timestamp('1900-03-01'):
            model_end = pd.Timestamp(model_end_str) + pd.Timedelta(days=1)  # Add on a day to account for the leap year in 1900
        else:
            model_end = pd.Timestamp(model_end_str) 

        return pd.date_range(start=model_start, end=model_end, freq='D')
    
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

        # Extract data depending on the variable type
        data_groups = {
            'normal': [],
            'soil': [],
            'radiation': [],
            }
        for var in vars:
            # Check if the variable is in the diagnostic dataset
            if var not in diagnostic.data_vars:
                # Variable will not be included in the output, give a warning
                print(f"Warning: Variable '{var}' not found in diagnostic '{diag}'. It will not be included in the output.")
                continue
            
            # Check the dimensions of the variable to determine its type
            if 'zfull_soil' in diagnostic[var].dims:
                # This is a soil variable, it will be handled separately
                data_groups['soil'].append(var)

            elif 'band' in diagnostic[var].dims:
                # This is a radiation variable, it will be handled separately
                data_groups['radiation'].append(var)

            elif 'grid_index' in diagnostic[var].dims and 'time' in diagnostic[var].dims:
                # This is a normal variable, it will be handled normally
                data_groups['normal'].append(var)

            else:
                # This variable isn't currently implemented, give a warning
                print(f"Warning: Variable '{var}' has unsupported dimensions {diagnostic[var].dims}. It will not be included in the output.")

        # Extract data for each group and combine
        data_frames = []
        if data_groups['normal']:
            normal_data = diagnostic[data_groups['normal']].isel(grid_index=0).to_dataframe()
            normal_data.index = self.get_gregorian_index(diag)
            # Drop unnecessary columns
            normal_data = normal_data.drop(columns=['grid_index', 'geolon_t', 'geolat_t'], errors='ignore')
            data_frames.append(normal_data)

        if data_groups['soil']:
            for soil_var in data_groups['soil']:
                soil_data = diagnostic[soil_var].isel(grid_index=0).to_dataframe()
                soil_data = soil_data.reset_index().pivot(index='time', columns='zfull_soil', values=soil_var)
                soil_data.columns.name = 'Depth'
                soil_data.index = self.get_gregorian_index(diag)
                soil_data.columns = [f"{soil_var} {col:03.2f}" for col in soil_data.columns]
                data_frames.append(soil_data)

        if data_groups['radiation']:
            # Not yet implemented, give warning
            print(f"Warning: Radiation variables {data_groups['radiation']} are not yet implemented. They will not be included in the output.")

        # Combine all data frames into a single DataFrame
        if data_frames:
            data = pd.concat(data_frames, axis=1)
        else:
            raise ValueError("No valid variables were provided or all variables are not implemented.")

        return data
    
    def close(self):
        '''
        Close any open diagnostic datasets.
        '''
        for diag in self.diagnostics.values():
            diag.close()