'''
Quick test for gamut functionality in model_datasets
'''
from model_datasets.gamut import GamutDataset

tonygrove = GamutDataset('Tony Grove')

# Get variables in the Gamut dataset
variables = tonygrove.get_variables()
print("Variables in the Gamut dataset:")
print(variables)

# Get data for a specific variable
data = tonygrove.get_data('BP_Avg')
print(data.head())