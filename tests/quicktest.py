'''
Initial quick testing
'''

from model_datasets.output import LM4ModelOutput

tony_grove = LM4ModelOutput('Tony Grove RS', '00000000', '1.0', spinup=True)

land_daily_vars = tony_grove.get_variables('land_daily')
print(land_daily_vars.head())

land_monthly_vars = tony_grove.get_variables('land_month')
print(land_monthly_vars.head())

testdata_daily = tony_grove.get_data(['snow_depth','soil_T'], 'land_daily')
print(testdata_daily.head())

testdata_monthly = tony_grove.get_data(['snow_density','soil_liq','average_T1','test'], 'land_month')
print(testdata_monthly.head())

tony_grove.close()
print("Quick test completed successfully.")