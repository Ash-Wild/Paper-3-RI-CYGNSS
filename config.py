# This file holds the configuration for the application. It includes settings for the database, API keys, and other environment-specific variables.

from pathlib import Path
import os 


data_dir = rf'C:\Users\{Path.home().name}\OneDrive - RMIT University\PHD\Data'
ri_events_nc_file = r'\IBTrACS.RI_events_v7.nc'
test_folder = r'\test_folder'

EARTHDATA_USERNAME = 'asiedlecki'
EARTHDATA_PASSWORD = 'RAPK8AKnA%Ghz0F1'
os.environ.setdefault("EARTHDATA_USERNAME", EARTHDATA_USERNAME)
os.environ.setdefault("EARTHDATA_PASSWORD", EARTHDATA_PASSWORD)

aws_or_local = 'local'  # 'aws' or 'local'
