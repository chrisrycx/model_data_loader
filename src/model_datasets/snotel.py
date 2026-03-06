'''
A class to describe PNNL Snotel data
'''

from typing import TypedDict
import pandas as pd
from datetime import datetime, date
from timezonefinder import TimezoneFinder
import os
import xarray as xr
import numpy as np

class SnotelData(TypedDict):
    T_max_C: float
    T_min_C: float
    T_avg_C: float
    precip_mm: float
    swe_mm: float

class PNNLSnotel:
    '''
    Class to store and manipulate the PNNL Snotel data.
    Does not load data by default so that the metadata can be used without needing to load the data.
    '''
    
    def __init__(self, site_name: str, storage_path: str):
        self.site_name = site_name
        self.data: pd.DataFrame = pd.DataFrame()
        self.latitude: float = 0.0
        self.longitude: float = 0.0
        self.elevation: float = 0.0

        # Load PNNL data path from environment variable
        self.SNOTEL_PATH = storage_path
        self.PNNL_DATA_PATH = os.path.join(storage_path, 'bcqc_data_v2')

        # Load the metadata and associated data
        self.file_name: str = '' #Initialize here, set during metadata load
        self.precise_location: bool = False
        self.load_metadata()
        self.check_location()
        self.timezone = self.get_timezone()
            
    def load_metadata(self):
        '''
        Load the metadata for the PNNL Snotel data.
        '''

        # Load the metadata file
        summary_file = os.path.join(self.PNNL_DATA_PATH, 'SNOTEL_summary.csv')

        # For each line in the metadata file, split the line by commas and search for site name in column 3
        site_match = False
        with open(summary_file) as f:
            for line in f:
                # Remove \n from the line
                line = line.strip()
                column_values = line.split(',')
                if column_values[3] == self.site_name:
                    site_match = True
                    self.elevation: float = int(column_values[4])/3.28  # Convert feet to meters
                    self.latitude: float = float(column_values[5])
                    self.longitude: float = float(column_values[6])
                    self.start_date: datetime = datetime.strptime(column_values[7], '%m/%d/%Y')
                    self.end_date: datetime = datetime.strptime(column_values[8], '%m/%d/%Y')
        
        if not site_match:
            raise ValueError(f"Site name {self.site_name} not found in the PNNL Snotel metadata file.")
        
        # Build the file name for the site. The file name uses the site latitude and longitude to 5 decimal places: "bcqc_latitude_longitude.txt"
        # Note! This needs to be done before data loading since the lat and long may be updated with more precise values
        self.file_name = f'bcqc_{self.latitude:.5f}_{self.longitude:.5f}.txt'
    
    def check_location(self):
        '''
        Check for more precise location in Detre data file
        '''
        # Load the Detre data file
        precise_locations = pd.read_csv(os.path.join(self.SNOTEL_PATH, 'SNOTEL_Detre.csv'))
        precise_locations.set_index('site_name', inplace=True)

        if self.site_name in precise_locations.index:
            # Some sites have precise latitude = 'NA', which becomes NaN, check for that
            if pd.notna(precise_locations.loc[self.site_name, 'latitude_precise']):
                self.latitude = precise_locations.loc[self.site_name, 'latitude_precise']
                self.longitude = precise_locations.loc[self.site_name, 'longitude_precise']
                self.elevation = precise_locations.loc[self.site_name, 'elevation_precise']
                self.precise_location = True

    def load_data(self):

        # Build the full path to the file
        rawfile = os.path.join(self.PNNL_DATA_PATH,'bcqc_data',self.file_name)

        # Read the txt file into a pandas dataframe. No header, separator is spaces
        snotel_data = pd.read_csv(rawfile, delimiter=r'\s+', header=None, names=['Year', 'Month', 'Day', 'Precipitation', 'Max Temp', 'Min Temp', 'Avg Temp', 'Snow Water Equivalent'])

        # convert Month, Day, Year to a datetime object and set as index
        snotel_data['Date'] = pd.to_datetime(snotel_data[['Year', 'Month', 'Day']])
        snotel_data.set_index('Date', inplace=True)
        snotel_data.drop(columns=['Year', 'Month', 'Day'], inplace=True)

        # Rename columns
        snotel_data.rename(columns={'Precipitation': 'precip_in', 'Max Temp': 'T_max_F', 'Min Temp': 'T_min_F', 'Avg Temp': 'T_avg_F', 'Snow Water Equivalent': 'swe_in'}, inplace=True)

        # Convert temperatures to C
        snotel_data['T_max_C'] = (snotel_data['T_max_F'] - 32) * 5/9
        snotel_data['T_min_C'] = (snotel_data['T_min_F'] - 32) * 5/9
        snotel_data['T_avg_C'] = (snotel_data['T_avg_F'] - 32) * 5/9

        # Convert precipitation and swe to mm
        snotel_data['precip_mm'] = snotel_data['precip_in'] * 25.4
        snotel_data['swe_mm'] = snotel_data['swe_in'] * 25.4

        self.data = snotel_data[['T_max_C', 'T_min_C', 'T_avg_C', 'precip_mm', 'swe_mm']].copy()

        # Localize the index to the timezone of the site
        self.data.index = self.data.index.tz_localize(self.timezone)

    def get_timezone(self):
        '''
        Get the timezone for the site.
        '''
        # Use the timezonefinder package to get the timezone for the site
        tf = TimezoneFinder()
        return tf.timezone_at(lng=self.longitude, lat=self.latitude)
    
    def find_usable_dates(self) -> tuple[date, date]:
        '''
        Determine what date range is usable for the snotel data.
        
        Returns: Dates (associated with local timezone) of the first and last day with usable data.
        '''
        if self.data.empty:
            raise ValueError(f"No data loaded for site {self.site_name}. Please load the data first.")

        # Find the first date in the index where the 'T_max_C', 'T_min_C', and 'precip_mm' columns are not NaN
        good_index: pd.DatetimeIndex = self.data.index[self.data['T_max_C'].notna() & self.data['T_min_C'].notna() & self.data['precip_mm'].notna()]
        
        # There should probably be at least 15 days of data to be minimally usable for testing
        if len(good_index) < 15:
            raise ValueError(f'Not enough usable data for site {self.site_name}. Only {len(good_index)} days of data found.')

        return (good_index[0].to_pydatetime().date(), good_index[-1].to_pydatetime().date())