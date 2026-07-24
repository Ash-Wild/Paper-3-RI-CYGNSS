# Purpose of this file is to match up the cygnss data with the storm data and create a new netcdf file with only the relevant variables from the storms.  

# open the storm data file and import relevant variables from config.py
from datetime import datetime

from a_config import ri_interpolated_nc_file, data_dir, aws_or_local, storm_lat_lon_buffer, cyg_dist_from_storm, cyg_time_from_storm, animate_storm, save_parquet_per_storm
from l1_access import check_cyg_l1_data
from utils import get_cygnss_files, find_valid_cygnss_indices, quadrant_from_storm
import netCDF4 as nc
import numpy as np
import pandas as pd
import os
import pyarrow # not used directly but needed as part of pandas to save parquet files


storm_interpolated_file = data_dir + ri_interpolated_nc_file
storm_interpolated_nc = nc.Dataset(storm_interpolated_file)

# get the relevant variables from the interpolated storm data
storm_ids = storm_interpolated_nc.variables['storm_id'][:]
storm_names = storm_interpolated_nc.variables['storm_name'][:]

storm_times = storm_interpolated_nc.variables['times_interp'][:]
storm_lats = storm_interpolated_nc.variables['latitude_interp'][:]
storm_lons = storm_interpolated_nc.variables['longitude_interp'][:]
storm_vmaxs = storm_interpolated_nc.variables['vmax_interp'][:]
storm_directions = storm_interpolated_nc.variables['direction_deg'][:]
storm_speeds = storm_interpolated_nc.variables['speed_kmh'][:]
storm_speed_changes = storm_interpolated_nc.variables['speed_change'][:]
storm_vmax_changes = storm_interpolated_nc.variables['vmax_change'][:]
storm_directions_changes = storm_interpolated_nc.variables['direction_change_deg'][:]
storm_start_ri_times = storm_interpolated_nc.variables['start_ri_time'][:]
storm_end_ri_times = storm_interpolated_nc.variables['end_ri_time'][:]
storm_intensities = storm_interpolated_nc.variables['intensities'][:]
storm_hemispheres = storm_interpolated_nc.variables['hemisphere'][:]
storm_initial_vmaxs = storm_interpolated_nc.variables['initial_vmax'][:]
storm_final_vmaxs = storm_interpolated_nc.variables['final_vmax'][:]

storm_interpolated_nc.close()

# extract the number of storms to evaluate for
if aws_or_local == 'aws_full':
    num_storms = range(len(storm_ids))
elif aws_or_local == 'local':
    num_storms = range(0, 2) # only evaluate the first two storms for testing purposes
else:
    num_storms = range(0, 2) # only evaluate the first two storms for testing purposes

all_storm_frames = []
meas_id = 0
meas_id_list = []
meas_len_list = []
brcs_blocks = []
eff_scatter_blocks = []

out_path = os.path.join(data_dir, "IBTrACS", "matched_")


for storm_idx in num_storms:
    matched_rows_storm = []
    cyg_times_storm = []
    cyg_lats_storm = []
    cyg_lons_storm = []

    storm_id = storm_ids[storm_idx]
    storm_name = storm_names[storm_idx]
    start_ri_time = storm_start_ri_times[storm_idx]
    end_ri_time = storm_end_ri_times[storm_idx]

    storm_times_i = np.array(storm_times[storm_idx])
    storm_lats_i = np.array(storm_lats[storm_idx])
    storm_lons_i = np.array(storm_lons[storm_idx])

    # check that the relevant cygnss files have been downloaded/accessible
    temporal = (storm_times_i[0], storm_times_i[-1])
    result = check_cyg_l1_data(temporal)
    if result == 'Bad':
        print(f"Failed to download required CYGNSS L1 data for storm {storm_name}.")
        continue

    lat_min = np.min(storm_lats_i) - storm_lat_lon_buffer
    lat_max = np.max(storm_lats_i) + storm_lat_lon_buffer
    lon_min = np.min(storm_lons_i) - storm_lat_lon_buffer
    lon_max = np.max(storm_lons_i) + storm_lat_lon_buffer

    # get the file names for the cygnss data that match the temporal range of the storm
    cygnss_files = get_cygnss_files(temporal)
    
    for file_idx in range(len(cygnss_files)):
        meas_id += 1
        with nc.Dataset(cygnss_files[file_idx]) as cyg_nc:
            # vars for finding relevant cygnss data
            # extend cyg_times so each entry is repeated 4 times, and flatten cyg_lats and cyg_lons so they are 1D arrays
            cyg_times = np.repeat(np.asarray(cyg_nc.variables['ddm_timestamp_utc'][:]), 4)
            cyg_lats = np.asarray(cyg_nc.variables['sp_lat'][:]).flatten()
            cyg_lons = np.asarray(cyg_nc.variables['sp_lon'][:]).flatten()

            # vars for machine learning analysis
            var = np.asarray(cyg_nc.variables['eff_scatter'][:])
            eff_scatter = var.reshape(var.shape[0] * var.shape[1], var.shape[2], var.shape[3])
            var = np.asarray(cyg_nc.variables['brcs'][:])
            brcs = var.reshape(var.shape[0] * var.shape[1], var.shape[2], var.shape[3])
            sp_inc_angle = np.asarray(cyg_nc.variables['sp_inc_angle'][:]).flatten()
            ddm_snr = np.asarray(cyg_nc.variables['ddm_snr'][:]).flatten()
            gps_eirp = np.asarray(cyg_nc.variables['gps_eirp'][:]).flatten()
            rx_to_sp_range = np.asarray(cyg_nc.variables['rx_to_sp_range'][:]).flatten()
            sc_vel_x_pvt = np.repeat(np.asarray(cyg_nc.variables['sc_vel_x_pvt'][:]), 4)
            sc_vel_y_pvt = np.repeat(np.asarray(cyg_nc.variables['sc_vel_y_pvt'][:]), 4)
            sc_vel_z_pvt = np.repeat(np.asarray(cyg_nc.variables['sc_vel_z_pvt'][:]), 4)
            sp_theta_orbit = np.asarray(cyg_nc.variables['sp_theta_orbit'][:]).flatten()
            tx_to_sp_range = np.asarray(cyg_nc.variables['tx_to_sp_range'][:]).flatten()
            quality_flags = np.asarray(cyg_nc.variables['quality_flags'][:]).flatten()
            sv_num = np.asarray(cyg_nc.variables['sv_num'][:]).flatten()
            ddm_ant = np.asarray(cyg_nc.variables['ddm_ant'][:]).flatten()
            nst_att_status = np.repeat(np.asarray(cyg_nc.variables['nst_att_status'][:]), 4)
            ddm_nbrcs = np.asarray(cyg_nc.variables['ddm_nbrcs'][:]).flatten()


        cyg_file_date_str = cygnss_files[file_idx].split("\\")[-1].split("-")[0].split("_")[0][-8:]
        # convert cyg_times so it is in same units as storm_times_arr. Change from seconds since start of day to seconds since 1970-01-01 00:00:00. I want it to remain as an integer
        cyg_date_seconds_int = int(datetime.strptime(cyg_file_date_str, "%Y%m%d").timestamp())
        cyg_times = np.asarray(cyg_times) + cyg_date_seconds_int

        spatial_mask, valid_idx, cyg_distances, cyg_time_diffs = find_valid_cygnss_indices(cyg_times, cyg_lats, cyg_lons, storm_times_i, storm_lats_i, storm_lons_i, lat_min, lat_max, lon_min, lon_max, cyg_dist_from_storm, cyg_time_from_storm)

        if valid_idx is None or len(valid_idx[0]) == 0:
            continue

        tc_indices = valid_idx[1]            # storm indices aligned to the filtered rows

        # select CYG fields once using the boolean mask (do not reapply valid_idx[0] again)
        cyg_times = cyg_times[spatial_mask][valid_idx[0]]
        cyg_lats = cyg_lats[spatial_mask][valid_idx[0]]
        cyg_lons = cyg_lons[spatial_mask][valid_idx[0]]



        eff_scatter = eff_scatter[spatial_mask][valid_idx[0]]
        brcs = brcs[spatial_mask][valid_idx[0]]
        sp_inc_angle = sp_inc_angle[spatial_mask][valid_idx[0]]
        ddm_snr = ddm_snr[spatial_mask][valid_idx[0]]
        gps_eirp = gps_eirp[spatial_mask][valid_idx[0]]
        rx_to_sp_range = rx_to_sp_range[spatial_mask][valid_idx[0]]
        sc_vel_x_pvt = sc_vel_x_pvt[spatial_mask][valid_idx[0]]
        sc_vel_y_pvt = sc_vel_y_pvt[spatial_mask][valid_idx[0]]
        sc_vel_z_pvt = sc_vel_z_pvt[spatial_mask][valid_idx[0]]
        sp_theta_orbit = sp_theta_orbit[spatial_mask][valid_idx[0]]
        tx_to_sp_range = tx_to_sp_range[spatial_mask][valid_idx[0]]
        quality_flags = quality_flags[spatial_mask][valid_idx[0]]
        sv_num = sv_num[spatial_mask][valid_idx[0]]
        ddm_ant = ddm_ant[spatial_mask][valid_idx[0]]
        nst_att_status = nst_att_status[spatial_mask][valid_idx[0]]
        ddm_nbrcs = ddm_nbrcs[spatial_mask][valid_idx[0]]

        # calculate the time of each measurement since the start of rapid  intensification (RI) and the time since the start of the storm
        time_since_ri_start_hr = (cyg_times - start_ri_time) # something wrong here, is 30 hours before
        time_since_storm_start_hr = (cyg_times - storm_times_i[0])

        # identify quadrant of each measurement relative to the storm center

        cyg_quadrants, cyg_direction = quadrant_from_storm(cyg_lats, cyg_lons, storm_lats_i, storm_lons_i, tc_indices, storm_directions[storm_idx], storm_hemispheres[storm_idx])

        # create a dataframe for the matched rows for this storm
        matched_rows_storm_i = pd.DataFrame({ 
            # # useful data but different lengths. Need place to go
            # "meas_id": meas_id,
            # 'storm_id': storm_id,
            # 'num_valid_cyg_measurements': len(cyg_times),
            # 'storm_intensity': storm_intensities[storm_idx],
            # 'storm_initial_intensity': storm_initial_vmaxs[storm_idx],
            # 'storm_final_intensity': storm_final_vmaxs[storm_idx],

            # # Not needed for future processing 
            # 'storm_name': storm_name,
            # 'storm_hemisphere': storm_hemispheres[storm_idx],
            # 'cyg_file_date': cyg_file_date_str,
            # 'storm_lat': storm_lats_i[tc_indices],
            # 'storm_lon': storm_lons_i[tc_indices],
            # 'cyg_time': cyg_times,
            # 'cyg_lat': cyg_lats,
            # 'cyg_lon': cyg_lons,

            'storm_vmax': storm_vmaxs[storm_idx][tc_indices],
            'storm_direction': storm_directions[storm_idx][tc_indices],
            'storm_speed': storm_speeds[storm_idx][tc_indices],
            'storm_speed_change': storm_speed_changes[storm_idx][tc_indices],
            'storm_vmax_change': storm_vmax_changes[storm_idx][tc_indices],
            'storm_direction_change': storm_directions_changes[storm_idx][tc_indices],

            'cyg_distance_from_storm_km': cyg_distances,
            'cyg_time_from_storm_min': cyg_time_diffs,
            'time_since_ri_start_hr': time_since_ri_start_hr,
            'time_since_storm_start_hr': time_since_storm_start_hr,
            'sp_inc_angle': sp_inc_angle,
            'ddm_snr': ddm_snr,
            'gps_eirp': gps_eirp,
            'rx_to_sp_range': rx_to_sp_range,
            'sc_vel_x_pvt': sc_vel_x_pvt,
            'sc_vel_y_pvt': sc_vel_y_pvt,
            'sc_vel_z_pvt': sc_vel_z_pvt,
            'sp_theta_orbit': sp_theta_orbit,
            'tx_to_sp_range': tx_to_sp_range,
            'quality_flags': quality_flags,
            'sv_num': sv_num,
            'ddm_ant': ddm_ant,
            'nst_att_status': nst_att_status,
            'ddm_nbrcs': ddm_nbrcs,
            'cyg_direction': cyg_direction,
            'cyg_quadrant': cyg_quadrants


            # 'eff_scatter': eff_scatter,
            # 'brcs': brcs,
        })
        matched_rows_storm.append(matched_rows_storm_i)

        meas_id_list.append(meas_id)
        meas_len_list.append(len(cyg_times))
        brcs_blocks.append(brcs)
        eff_scatter_blocks.append(eff_scatter)
        cyg_times_storm.extend(cyg_times)
        cyg_lats_storm.extend(cyg_lats)
        cyg_lons_storm.extend(cyg_lons)

    if len(matched_rows_storm) == 0:
        continue

    storm_df = pd.concat(matched_rows_storm, ignore_index=True)
    
    if save_parquet_per_storm:

        storm_df.to_parquet(f"{out_path}{storm_id}.parquet", index=False)

        brcs_array = np.concatenate(brcs_blocks, axis=0)
        eff_scatter_array = np.concatenate(eff_scatter_blocks, axis=0)
        np.savez_compressed(
            f"{out_path}{storm_id}_ddm.npz",
            meas_id=meas_id_list,
            meas_len=meas_len_list,
            brcs=brcs_array,
            eff_scatter=eff_scatter_array,
        )
        meas_id_list = []
        meas_len_list = []
        brcs_blocks = []
        eff_scatter_blocks = []
    else:
        all_storm_frames.append(storm_df)

    if animate_storm:
        from utils import create_storm_animation
        create_storm_animation(storm_id, storm_name, storm_times_i, storm_lats_i, storm_lons_i, storm_vmaxs[storm_idx], storm_directions[storm_idx], storm_df, cyg_times_storm, cyg_lats_storm, cyg_lons_storm)

if not save_parquet_per_storm:
    all_storms_df = pd.concat(all_storm_frames, ignore_index=True)
    all_storms_df.to_parquet(f"{out_path}all_storms.parquet", index=False)
    brcs_array = np.concatenate(brcs_blocks, axis=0)
    eff_scatter_array = np.concatenate(eff_scatter_blocks, axis=0)
    np.savez_compressed(
        f"{out_path}all_storms_ddm.npz",
        meas_id=meas_id_list,
        meas_len=meas_len_list,
        brcs=brcs_array,
        eff_scatter=eff_scatter_array,
    )