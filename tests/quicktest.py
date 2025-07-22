'''
Initial quick testing
'''

from model_datasets.datasets import LM4ModelOutput

tony_grove = LM4ModelOutput('Tony Grove RS', '00000000', '1.0', spinup=True)

land_daily_vars = tony_grove.get_variables('land_daily')
print(land_daily_vars.head())

land_monthly_vars = tony_grove.get_variables('land_month')
print(land_monthly_vars.head())

testdata = tony_grove.get_data(['t_ref', 'snow_frac', 'snow_depth'], 'land_daily')
print(testdata.head())

tony_grove.close()
print("Quick test completed successfully.")