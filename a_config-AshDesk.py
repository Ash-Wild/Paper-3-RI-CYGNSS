# This file holds the configuration for the application. It includes settings for the database, API keys, and other environment-specific variables.

from pathlib import Path
import os 


data_dir = rf'C:\Users\{Path.home().name}\OneDrive - RMIT University\PHD\Data'
ri_events_version = '8'
ri_events_nc_file = rf'\IBTrACS\RI_events_v{ri_events_version}.nc'
ri_interpolated_nc_file = rf'\IBTrACS\RI_events_v{ri_events_version}_interpolated.nc'
test_folder = r'\test_folder'

EARTHDATA_USERNAME = 'asiedlecki'
EARTHDATA_PASSWORD = 'RAPK8AKnA%Ghz0F1'
os.environ.setdefault("EARTHDATA_USERNAME", EARTHDATA_USERNAME)
os.environ.setdefault("EARTHDATA_PASSWORD", EARTHDATA_PASSWORD)

aws_or_local = 'local'  # 'aws_full' or 'local' or 'aws_test'

# File b
# mode - either create or analyse. Create will run the code to find RI events and save to a new netCDF file. Analyse will load the saved file and run some basic analysis on it.
ri_nc_mode = 'create'# 'create' # 'analyse'
# Time intervals (in hours) to check for RI events
time_thresholds = [24] # [6, 12, 24]
# Wind speed thresholds (in knots) for identifying RI intensity changes
wind_thresholds = [45, 30, 25, 20]

# File c
compare_interp = False # If True, compare the spline and linear interpolation methods for storm tracks.
spline_interp_order = 2 # Order of the spline interpolation. 1 is linear, 2 is quadratic, 3 is cubic, etc.
interp_time = 5  # minutes
view_animation = False # If True, create an animation of the storm's movement and intensity over time, with the interpolated points and the rate of change of the storm's direction, speed, and intensity displayed on the animation. The direction of the storm's movement will be represented by an arrow, the speed of the storm will be represented by the length of the arrow, and the intensity of the storm will be represented by the color of the arrow. The rate of change of the storm's direction, speed, and intensity will be represented by a graph displayed on the animation.

# file d
cyg_dist_from_storm = 100 # km. The distance from the storm center to consider for matching CYGNSS data with the storm data.
cyg_time_from_storm = 10 # minutes. The time from the storm center to consider for matching CYGNSS data with the storm data.
storm_lat_lon_buffer = 1.3 # degrees. The buffer around the storm's lat/lon to consider for matching CYGNSS data with the storm data.
animate_storm = True # If True, create an animation of the storm's movement and intensity over time, with the matched CYGNSS data points displayed on the animation