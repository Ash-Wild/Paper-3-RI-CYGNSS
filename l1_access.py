# script to access l1 data either on AWS or locally 


import os
from pathlib import Path

from a_config import aws_or_local, data_dir, EARTHDATA_USERNAME, EARTHDATA_PASSWORD, test_folder

def download_cyg_l1_temporal(temporal):
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
    # 1 Check if dates within file names already exist in the download directory before calling the earthaccess_api function
    download_dir = data_dir + test_folder
    existing_files = os.listdir(download_dir)
    existing_files = [f.split('.s')[1][:8] for f in existing_files]
    
    
    # make a list of temporal range of strings 'YYYYMMDD' for each day in the temporal range
    from datetime import datetime, timedelta
    start_date = datetime.strptime(temporal[0], '%Y-%m-%d')
    end_date = datetime.strptime(temporal[1], '%Y-%m-%d')
    temporal_range = [(start_date + timedelta(days=i)).strftime('%Y%m%d') for i in range((end_date - start_date).days + 1)]

    # Filter temporal range only include files that do not already exist in the download directory and give the new temporal range to the earthaccess_api function
    temporal_range = [date for date in temporal_range if date not in existing_files]
    temporal = (temporal_range[0], temporal_range[-1]) if temporal_range else None

    if temporal is None:
        # print("No new files to download.")
        return 'Good'
    
    # 3 Search
    import earthaccess
    earthaccess.login(strategy="environment")
    results = earthaccess.search_data(
        short_name='CYGNSS_L1_V3.2',  # 
        bounding_box=(150, -40, 160, 40),  # Only include files in area of interest...
        temporal=temporal,  # ...and time period of interest.
        count= 2 #-1 for all
    )
    if results is None or len(results) == 0:
        return 'Bad'
    
    print(f'Downloaded files to {download_dir}')
    files = earthaccess.download(results, str(download_dir))
    return 'Good'

def check_cyg_l1_data(temporal):
    """
    Checks if the required CYGNSS L1 data files are available locally or on AWS.

    Parameters:
    temporal (tuple): A tuple containing the start and end dates for the temporal range (start_date, end_date).

    Returns:
    None
    """

    # check if the temporal value is in seconds or in the format 'YYYY-MM-DD' and convert to 'YYYY-MM-DD' if in seconds
    start_time, end_time = temporal
    import numpy as np

    if isinstance(start_time, np.ndarray):
        start_time = start_time.item() if start_time.size == 1 else start_time[0]
    if isinstance(end_time, np.ndarray):
        end_time = end_time.item() if end_time.size == 1 else end_time[0]

    if isinstance(start_time, (np.integer, int, float)):
        from datetime import datetime
        temporal = (
            datetime.utcfromtimestamp(float(start_time)).strftime('%Y-%m-%d'),
            datetime.utcfromtimestamp(float(end_time)).strftime('%Y-%m-%d')
        )

    
    if aws_or_local == 'aws_full':
        # Check if the required files are available on AWS
        # Implement your logic to check AWS availability here
        pass
    elif aws_or_local == 'local':
        # Check if the required files are available locally
        download_cyg_l1_temporal(temporal)
