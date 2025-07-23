'''
Initial quick testing of forcing class
'''

from model_datasets.forcing import LM4Forcing

tony_grove = LM4Forcing('Tony Grove RS', '00000000', '0.1', spinup=True)

# Get variables in the forcing dataset
variables_df = tony_grove.get_variables()
print("Variables in the forcing dataset:")
print(variables_df.head())

# Get data for a specific variable
Tair = tony_grove.get_data('Tair')
print("Tair data sample:")
print(Tair.head())

# Get looped data for a specific variable
looped_Tair = tony_grove.get_looped_data('Tair', spin_up_years=20)
print("Looped Tair data sample:")
print(looped_Tair.head())

tony_grove.close()
print("Quick test completed successfully.")