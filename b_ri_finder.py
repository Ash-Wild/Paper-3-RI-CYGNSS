# -*- coding: utf-8 -*-
"""
Created on Sat Jan 27 07:21:02 2024
Purpose: determine best RI events in best-track data
Input: IBTrACS dataset
Output: List of RI events, time and lat and lon. 
@author: ashle
"""
import netCDF4 as nc
import numpy as np 
from pathlib import Path

from a_config import time_thresholds, wind_thresholds, ri_events_version, ri_nc_mode as mode, aws_or_local
# Lists to store identified RI event data
storm_ids = []
storm_names = []
inds_before = []  # Index before the RI event for context
inds_after = []   # Index after the RI event for context
times = []        # Timestamps for each RI event
lats = []         # Latitude coordinates
lons = []         # Longitude coordinates
winds = []        # Wind speeds throughout the event
duration = []     # Duration of the event in hours
intensity = []    # Wind speed threshold met for the event

path = Path.home() / 'OneDrive - RMIT University' / 'PHD' / 'Data' / 'IBTrACS'
file_name = 'IBTrACS.since1980.v04r01.nc'  # 'IBTrACS.last3years.v04r00.nc'
RI_file = path / f'RI_events_v{ri_events_version}.nc'

if mode == 'create':
    IB_nc = nc.Dataset(str(path / file_name))
    WMO_wind = IB_nc.variables['wmo_wind'][:]
    wmo_agency = IB_nc.variables['wmo_agency']
    storm_id = IB_nc.variables['sid'][:].astype(str)
    storm_name = IB_nc.variables['name'][:].astype(str)
    dt_str = IB_nc.variables['iso_time'][:].astype('U2')
    lat = IB_nc.variables['lat'][:]
    lon = IB_nc.variables['lon'][:]

    rows, cols, depth = dt_str.shape
    dt_concatenated = np.empty((rows, cols))
    storm_id_concatenated = np.zeros((rows)).astype(str) 

    for i in range(rows):
        storm_id_concatenated[i] = np.array([''.join(storm_id[i,:])])[0]
        
        for j in range(cols):
            if not type(dt_str[i,j,0]) == np.ma.core.MaskedConstant:
                dt_concatenated[i,j]= np.array([''.join(dt_str[i,j,:])],dtype = 'datetime64[s]')[0]

    # find locations of RI
    from datetime import datetime, timedelta
    dt= dt_concatenated.astype(datetime)

    for wind_threshold in wind_thresholds:
        time_threshold = time_thresholds[0]  # Assuming you want to use the first time threshold for this loop
        for tc in range(rows):
            start_ind = 0 ; end_ind = 1
            counter = 0
            storm_datetime = np.datetime64('1970-01-01T00:00:00') + np.timedelta64(int(dt[tc,end_ind]), 's')

            if aws_or_local == 'local':
                start_time = '2019-01-01'
            else:
                start_time = '2018-08-01'

            if storm_datetime >= np.datetime64(start_time): # only run for Valid CYGNSS years.
                while dt[tc,end_ind] > 1 and counter <cols*2: 
                    counter+=1
                    time_difference = (dt[tc,end_ind] - dt[tc,start_ind])/60/60 # convert from seconds to hours
                    if time_difference < time_threshold:
                        end_ind += 1
                        if end_ind >= cols: # if it makes it to the end of array
                            break 
                    elif time_difference > time_threshold:
                        start_ind =+ 1
            
                    elif time_difference == time_threshold and np.nan not in [WMO_wind[tc,end_ind], WMO_wind[tc,start_ind]]:
                        WMO_wind_dif = WMO_wind[tc,end_ind] - WMO_wind[tc,start_ind]
                        
                        # update storm_name to be a simple string of the name instead of an array of characters
                        storm_name_clean = ''.join(
                            str(char) for char in storm_name[tc]
                            if not isinstance(char, np.ma.core.MaskedConstant)
                        ).strip()
                        start_ind_before = np.abs(dt[tc]-(dt[tc,start_ind]-43200)).argmin() # np.
                        end_ind_after = np.abs(dt[tc]-(dt[tc,end_ind]+43200)).argmin() # add 12 hours of context before and after the event, find the closest time index to that
                        ind_before = start_ind - start_ind_before ; ind_after = end_ind_after - end_ind
                        if WMO_wind_dif >= wind_threshold and storm_id_concatenated[tc] not in storm_ids:
                            storm_ids.append(storm_id_concatenated[tc])  
                            storm_names.append(storm_name_clean)
                            inds_before.append(ind_before); inds_after.append(ind_after)
                            times.append(dt[tc,start_ind_before:end_ind_after])
                            lats.append(lat[tc,start_ind_before:end_ind_after])
                            lons.append(lon[tc,start_ind_before:end_ind_after])
                            duration.append(time_difference)
                            intensity.append(wind_threshold)
                            winds.append(WMO_wind[tc,start_ind_before:end_ind_after])

                            break

                        start_ind += 1
                            
                    else:
                        start_ind += 1
        
    # saving the details

    def padding(data,max_len):
        # input data list of numpy arrays and adds numpy nan to the end so all the arrays are same length
        import numpy as np
        padded_data=np.ma.MaskedArray(np.full((len(data), max_len), np.nan))
        # padded_data.data =   # Create 2D array filled with NaN
        for i, arr in enumerate(data):
            padded_data[i, :len(arr)] = arr  # Fill in values from each array
            
        return padded_data
            
            
    import netCDF4 as nc
    with nc.Dataset(str(RI_file), 'w') as ncfile:
        max_len = max(len(arr) for arr in times)
        # Pad arrays to the same length with NaN
        times_padded = padding(times,max_len)  
        lats_padded = padding(lats,max_len)  
        lons_padded = padding(lons,max_len)  
        winds_padded = padding(winds,max_len)
        new_mask = np.isnan(winds_padded.data) | (winds_padded.data < 0)     # Create new condition mask: values < 0 or NaN
        winds_padded.mask = winds_padded.mask | new_mask     # Combine old and new masks
        # Create dimensions
        length = len(storm_ids)
        ncfile.createDimension('events', length)
        ncfile.createDimension('values', max_len)
        
        # Create variables
        time = ncfile.createVariable('times', 'f8', ('events','values'))
        storm_id = ncfile.createVariable('storm_id', str, ('events',))
        storm_name = ncfile.createVariable('storm_name', str, ('events',))
        latitude = ncfile.createVariable('latitude', 'f4', ('events','values'))
        longitude = ncfile.createVariable('longitude', 'f4', ('events','values'))
        vmax = ncfile.createVariable('vmax', 'f4', ('events','values'))
        durations = ncfile.createVariable('durations', 'i4', ('events',))
        intensities = ncfile.createVariable('intensities', 'i4', ('events',))
        index_before = ncfile.createVariable('index_before', 'i4', ('events',))
        index_after = ncfile.createVariable('index_after', 'i4', ('events',))


        # Add data to variables
        time[:] = times_padded
        storm_id[:] = np.array(storm_ids,dtype="object")
        storm_name[:] = np.array(storm_names,dtype="object")
        latitude[:] = lats_padded
        longitude[:] = lons_padded
        vmax[:] = winds_padded
        durations[:] = duration
        intensities[:] = intensity
        index_after[:] = inds_after
        index_before[:] = inds_before
    
    # save also as a csv file for easier access
    import pandas as pd

    # update the times to be a string of the format 'YYYY-MM-DD HH:MM:SS' for easier reading in the csv file, and only include the times that are not NaN
    times_str = []
    times_datetime = np.datetime64('1970-01-01T00:00:00') + np.array(times_padded).astype('timedelta64[s]')
    for time_array in times_datetime:
        time_str_array = []
        for time in time_array:
            if not np.isnan(time):
                time_str_array.append(time.astype(str))

            else:
                time_str_array.append(np.nan)
        times_str.append(time_str_array)

    df = pd.DataFrame({
        'storm_id': storm_ids,
        'storm_name': storm_names,
        'times': times_str,
        'latitude': lats,
        'longitude': lons,
        'vmax': winds,
        'durations': duration,
        'intensities': intensity,
        'index_before': inds_before,
        'index_after': inds_after
    })
    df.to_csv(path / f'RI_events_v{ri_events_version}.csv', index=False)

if mode == 'analyse':
    RI_nc = nc.Dataset(str(RI_file))
    times = RI_nc.variables['times'][:]
    storm = RI_nc.variables['storm_id'][:]
    latitude = RI_nc.variables['latitude'][:]
    longitude = RI_nc.variables['longitude'][:]
    vmax = RI_nc.variables['vmax'][:]
    durations = RI_nc.variables['durations'][:]
    intensities = RI_nc.variables['intensities'][:]
    index_before = RI_nc.variables['index_before'][:]
    index_after = RI_nc.variables['index_after'][:]

    # print summary statistics for the stored RI events
    total_events = len(storm)
    print(f'Total events: {total_events}')

    # print the average duration and intensity across all events
    avg_duration = np.mean(durations)
    avg_intensity = np.mean(intensities)
    print(f'Average duration of events: {avg_duration} hours')
    print(f'Average intensity of events: {avg_intensity} knots')

    # print the number of unique storms at each time and intensity threshold
    for time_threshold in time_thresholds:
        for wind_threshold in wind_thresholds:
            storms_at_threshold = set(storm[(durations == time_threshold) & (intensities == wind_threshold)])
            print(f'Time threshold: {time_threshold} hours, Wind threshold: {wind_threshold} knots, Unique storms: {len(storms_at_threshold)}')

    # determine how many storms cross the longitude of 180 and 360 during an RI event
    storms_crossing_180 = 0
    storms_crossing_360 = 0

    def check_crossing(longitudes):
        # Check if the storm crosses the 180 or 360 longitude
        crosses_180 = np.any(longitudes > 180) and np.any(longitudes < -180)
        crosses_360 = np.any(longitudes > 360) and np.any(longitudes < 0)
        return crosses_180, crosses_360

    for i in range(total_events):
        crosses_180, crosses_360 = check_crossing(longitude[i,:])
        if crosses_180:
            storms_crossing_180 += 1
        if crosses_360:
            storms_crossing_360 += 1
    print(f'Storms crossing longitude 180: {storms_crossing_180}')
    print(f'Storms crossing longitude 360: {storms_crossing_360}')