'''
A class for managing forcing datasets.
'''
import os
import pandas as pd
import xarray as xr

# Load paths from environment variables
FORCING_PATH = os.getenv('FORCING_PATH', None)
if FORCING_PATH is None:
    raise ValueError("FORCING_PATH environment variable is not set.")


class LM4Forcing:
    def __init__(self, site: str, forcing_string: str, version: str, spinup=False):
        '''
        Initialize the LM4Forcing class.
        :param site: Site name (e.g., 'Tony Grove RS'). Can use Snotel or model name.
        :param forcing_string: Forcing string (e.g., 00000000)
        :param version: Version of the forcing dataset (e.g., '0.1')
        :param spinup: Whether the dataset is a spinup version
        '''
        self.site = site.replace(' ', '').lower()
        
        # Construct the path to the forcing dataset
        if spinup:
            self.forcing_path = os.path.join(FORCING_PATH, self.site, f'{self.site}_spinup_s{forcing_string}_v{version}.nc')
        else:
            self.forcing_path = os.path.join(FORCING_PATH, self.site, f'{self.site}_s{forcing_string}_v{version}.nc')

        # Open the forcing dataset
        self.netcdf = xr.open_dataset(self.forcing_path)

    def get_variables(self) -> pd.DataFrame:
        '''
        Returns a DataFrame with the variables in the forcing dataset.
        :return: DataFrame with variable names, dimensions, long names, and units
        '''
        vars_df = pd.DataFrame({
            'dimensions': [self.netcdf[var].dims for var in self.netcdf.data_vars],
            'long_name': [self.netcdf[var].attrs.get('long_name', '') for var in self.netcdf.data_vars],
            'units': [self.netcdf[var].attrs.get('units', '') for var in self.netcdf.data_vars]
        }, index=self.netcdf.data_vars)

        return vars_df
    
    def get_data(self, var_name: str) -> pd.Series:
        '''
        Get data for a specific variable.
        :param var_name: Name of the variable to retrieve
        :return: Pandas Series with the data for the specified variable
        '''
        if var_name not in self.netcdf.data_vars:
            raise ValueError(f"Variable '{var_name}' not found in the dataset.")
        
        # Convert to series and set the index to the 'time' dimension
        return self.netcdf[var_name].isel(latitude=0, longitude=0).to_series()
    
    
    def get_looped_data(self, var_name: str, spin_up_years: int) -> pd.Series:
        '''
        Approximates the looped forcing used by the model. It won't be exactly the same because the model
        uses an interpolation algorithm to loop the data, but this will be sufficient for most purposes.
        :param var_name: Name of the variable to retrieve
        :param spin_up: Spinup period in years (must be a multiple of 10)
        :return: Pandas Series with the daily looped data for the specified variable
        '''
        # Ensure that spin_up_years is a multiple of 10
        if spin_up_years % 10 != 0:
            raise ValueError("Spinup years must be a multiple of 10.")

        # Extract the variable data
        data = self.netcdf[var_name].isel(latitude=0, longitude=0).to_series()

        # Resample to daily frequency
        data_daily = data.resample('D').mean()

        # Loop the data for the spinup period
        # The model uses an interpolation algorithm to do the looping, but concatenating the data is sufficient for this purpose.
        # I need to leave off the last day of the data when concatenating because the spinup start and end on the same day.
        looped = pd.concat([data_daily[:-1]] * int(spin_up_years / 10), ignore_index=True)

        # Generate a new index that starts at the first day of the model run
        # This index will be gregorian. The model uses Julian, but for the date ranges of interest, this is sufficient.
        model_start_year = data_daily.index[-1].year - spin_up_years
        model_start = data_daily.index[0].replace(year=model_start_year)
        looped.index = pd.date_range(start=model_start, periods=len(looped), freq='D')

        # Shift index by 12 hours to match model output
        looped.index = looped.index + pd.Timedelta(hours=12)
        looped.name = var_name

        return looped
    
    def close(self):
        '''
        Close the xarray dataset.
        '''
        self.netcdf.close()