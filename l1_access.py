# script to access l1 data either on AWS or locally 


import os
from pathlib import Path

from config import aws_or_local, data_dir, EARTHDATA_USERNAME, EARTHDATA_PASSWORD, test_folder

def earthaccess_api(bounding_box, temporal, count=2):
    """
    Accesses the Earthdata API to search and download data based on the provided parameters.

    Parameters:
    bounding_box (tuple): A tuple containing the coordinates of the bounding box (min_lon, min_lat, max_lon, max_lat).
    temporal (tuple): A tuple containing the start and end dates for the temporal range (start_date, end_date).
    short_name (str): The short name of the dataset to search for. Default is 'ATL06'.
    count (int): The number of results to return. Default is 2.

    Returns:
    list: A list of downloaded files.
    """
    import earthaccess

    earthaccess.login(strategy="environment")
    download_dir = data_dir + test_folder

    # 2. Search
    results = earthaccess.search_data(
        short_name='CYGNSS_L1_V3.2',  # 
        bounding_box=bounding_box,  # Only include files in area of interest...
        temporal=temporal,  # ...and time period of interest.
        count=-1
    )

    # 3. Access
    print(f'Downloaded files to {download_dir}')
    files = earthaccess.download(results, str(download_dir))

if aws_or_local == 'local':
    bounding_box = (150, -40, 160, -30)  # Example bounding box (min_lon, min_lat, max_lon, max_lat)
    temporal = ('2020-01-01', '2020-12-31')  # Example temporal range (start_date, end_date)

    # need to check if files already exist in the download directory before calling the earthaccess_api function
    download_dir = data_dir + test_folder

    earthaccess_api(bounding_box, temporal)