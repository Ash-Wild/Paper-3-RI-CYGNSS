# purpose is to analyse the IBTrACS RI data and compare it to the CYGNSS L1 data. The analysis will be done in a Jupyter notebook, but this script will be used to access the data either on AWS or locally.
# 
from a_config import interp_time, data_dir, ri_events_nc_file, compare_interp, spline_interp_order, view_animation, ri_interpolated_nc_file
from utils import haversine_km, angle_deg
import numpy as np
import netCDF4 as nc
from scipy.interpolate import make_interp_spline


# load the RI IBTrACS data
ri_events_file = data_dir + ri_events_nc_file
ri_events_nc = nc.Dataset(ri_events_file)
storm_times = ri_events_nc.variables['times'][:]
storm_lats = ri_events_nc.variables['latitude'][:]
storm_lons = ri_events_nc.variables['longitude'][:]
storm_vmaxs = ri_events_nc.variables['vmax'][:]     
storm_ids = ri_events_nc.variables['storm_id'][:]
storm_names = ri_events_nc.variables['storm_name'][:]
storm_intensities = ri_events_nc.variables['intensities'][:]
storm_inds_after = ri_events_nc.variables['index_after'][:]
storm_inds_before = ri_events_nc.variables['index_before'][:]

# store results for the output file
out_storm_ids = []
out_storm_names = []
out_hemisphere = []
out_times = []
out_lats = []
out_lons = []
out_vmaxs = []
out_speed_kmh = []
out_direction_deg = []
out_vmax_change = []
out_speed_change = []
out_direction_change_deg = []
out_start_ri_time = []
out_end_ri_time = []
out_intensities = []
out_vmax_initial = []
out_vmax_final = []

# for each storm, interpolate the data to 30 minute intervals using spline and linearly. 
for i in range(len(storm_ids)):
    non_nan_inds = ~np.isnan(storm_times[i])
    storm_time = storm_times[i][non_nan_inds]
    storm_lat = storm_lats[i][non_nan_inds]
    storm_lon = storm_lons[i][non_nan_inds]
    storm_vmax = storm_vmaxs[i][non_nan_inds]
    storm_times_interp = np.arange(storm_time[0], storm_time[-1], interp_time*60) 
    lat_spline = make_interp_spline(storm_time, storm_lat, k=spline_interp_order)
    lon_spline = make_interp_spline(storm_time, storm_lon, k=spline_interp_order)
    vmax_spline = make_interp_spline(storm_time, storm_vmax, k=spline_interp_order)

    storm_lats_interp = lat_spline(storm_times_interp)
    storm_lons_interp = lon_spline(storm_times_interp)
    storm_vmaxs_interp = vmax_spline(storm_times_interp)

    storm_lats_interp_linear = np.interp(storm_times_interp, storm_time, storm_lat)
    storm_lons_interp_linear = np.interp(storm_times_interp, storm_time, storm_lon)
    storm_vmaxs_interp_linear = np.interp(storm_times_interp, storm_time, storm_vmax)

    # optional add a plot of the storm track and the interpolated points to check that the interpolation is working correctly.
    if compare_interp:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 5))
        plt.plot(storm_lons_interp, storm_lats_interp, 'r-', label='Spline Interpolation')
        plt.plot(storm_lons_interp_linear, storm_lats_interp_linear, 'b--', label='Linear Interpolation')
        plt.scatter(storm_lon, storm_lat, c='k', label='Original Data')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title(f'Storm {storm_ids[i]} Track Interpolation Comparison')
        plt.legend()
        plt.grid()
        plt.show()    


    # calculate the direction that the storm is moving in and the speed of the storm at each interpolated point.
    dist_km = haversine_km(
        storm_lats_interp[:-1],
        storm_lons_interp[:-1],
        storm_lats_interp[1:],
        storm_lons_interp[1:]
    )
    dt_hours = np.diff(storm_times_interp)/60/60
    storm_speed_kmh = dist_km / dt_hours
    storm_direction_deg = angle_deg(
        storm_lats_interp[:-1],
        storm_lons_interp[:-1],
        storm_lats_interp[1:],
        storm_lons_interp[1:]
    )

    # calculate the rate of change of the storm's direction, speed, and intensity at each interpolated point. 
    # use midpoint times for variables defined between track points
    storm_mid_times = storm_times_interp[:-1] + (np.diff(storm_times_interp) / 2)

    # convert seconds to hours for clearer rates
    storm_mid_times_hours = (storm_mid_times - storm_mid_times[0]) / 3600.0
    storm_times_interp_hours = (storm_times_interp - storm_times_interp[0]) / 3600.0

    # rate of change of speed
    storm_speed_change = np.gradient(storm_speed_kmh, storm_mid_times_hours)

    # rate of change of direction
    storm_direction_rad = np.unwrap(np.radians(storm_direction_deg))
    storm_direction_change_rad = np.gradient(storm_direction_rad, storm_mid_times_hours)
    storm_direction_change_deg = np.degrees(storm_direction_change_rad)

    # rate of change of intensity
    storm_vmax_change = np.gradient(storm_vmaxs_interp, storm_times_interp_hours)
    # use midpoint times for variables defined between track points
    storm_mid_times = storm_times_interp[:-1] + (np.diff(storm_times_interp) / 2)

    # convert seconds to hours for clearer rates
    storm_mid_times_hours = (storm_mid_times - storm_mid_times[0]) / 3600.0
    storm_times_interp_hours = (storm_times_interp - storm_times_interp[0]) / 3600.0

    # rate of change of speed
    storm_speed_change = np.gradient(storm_speed_kmh, storm_mid_times_hours)

    # rate of change of direction
    storm_direction_rad = np.unwrap(np.radians(storm_direction_deg))
    storm_direction_change_rad = np.gradient(storm_direction_rad, storm_mid_times_hours)
    storm_direction_change_deg = np.degrees(storm_direction_change_rad)

    # rate of change of intensity
    storm_vmax_change = np.gradient(storm_vmaxs_interp, storm_times_interp_hours)

    # hemisphere of the storm. If the latitude is positive, it is in the northern hemisphere, otherwise it is in the southern hemisphere.
    if storm_lats_interp[0] > 0:
        out_hemisphere.append(1) # Northern Hemisphere
    else:
        out_hemisphere.append(-1) # Southern Hemisphere

    # visualise
    if view_animation:
        from utils import make_animation
        make_animation(
            storm_times_interp,
            storm_lats_interp,
            storm_lons_interp,
            storm_vmaxs_interp,
            storm_speed_kmh,
            storm_direction_deg,
            storm_vmax_change,
            storm_speed_change,
            storm_direction_change_deg, 
            storm_ids[i],
            storm_names[i]
        )
    
    #  bundle the interpolated data to a single new netCDF file. The file will be saved in the same directory as the original file, with the name 'RI_events_v{ri_events_version}_interpolated.nc'.
    
    # pad 1-point-short arrays to match storm_times_interp length
    storm_speed_kmh = np.append(storm_speed_kmh, storm_speed_kmh[-1])
    storm_direction_deg = np.append(storm_direction_deg, storm_direction_deg[-1])
    storm_vmax_change = np.append(storm_vmax_change, storm_vmax_change[-1])
    storm_speed_change = np.append(storm_speed_change, storm_speed_change[-1])
    storm_direction_change_deg = np.append(storm_direction_change_deg, storm_direction_change_deg[-1])

    # save results for writing later
    out_storm_ids.append(storm_ids[i].decode() if isinstance(storm_ids[i], bytes) else str(storm_ids[i]))
    out_storm_names.append(storm_names[i].decode() if isinstance(storm_names[i], bytes) else str(storm_names[i]))
    out_start_ri_time.append(storm_time[storm_inds_before[i]].astype(np.int64))
    out_end_ri_time.append(storm_time[-storm_inds_after[i]].astype(np.int64))    
    out_intensities.append(storm_intensities[i].astype(np.float32))
    out_vmax_initial.append(storm_vmax[storm_inds_before[i]])
    out_vmax_final.append(storm_vmax[-storm_inds_after[i]])

    out_times.append(storm_times_interp.astype(np.int64))
    out_lats.append(storm_lats_interp.astype(np.float32))
    out_lons.append(storm_lons_interp.astype(np.float32))
    out_vmaxs.append(storm_vmaxs_interp.astype(np.float32))
    out_speed_kmh.append(storm_speed_kmh.astype(np.float32))
    out_direction_deg.append(storm_direction_deg.astype(np.float32))
    out_vmax_change.append(storm_vmax_change.astype(np.float32))
    out_speed_change.append(storm_speed_change.astype(np.float32))
    out_direction_change_deg.append(storm_direction_change_deg.astype(np.float32))


# after the interpolation loop, write the output file
out_file = data_dir + ri_interpolated_nc_file

with nc.Dataset(out_file, "w", format="NETCDF4") as ds:
    ds.createDimension("storm", len(out_storm_ids))

    vlen_i8 = ds.createVLType(np.int64, "vlen_i8")
    vlen_f4 = ds.createVLType(np.float32, "vlen_f4")

    storm_id_var = ds.createVariable("storm_id", str, ("storm",))
    storm_name_var = ds.createVariable("storm_name", str, ("storm",))
    storm_hemisphere_var = ds.createVariable("hemisphere", np.int8, ("storm",))
    storm_initial_vmax_var = ds.createVariable("initial_vmax", np.float32, ("storm",))
    storm_final_vmax_var = ds.createVariable("final_vmax", np.float32, ("storm",))
    times_var = ds.createVariable("times_interp", vlen_i8, ("storm",))
    lat_var = ds.createVariable("latitude_interp", vlen_f4, ("storm",))
    lon_var = ds.createVariable("longitude_interp", vlen_f4, ("storm",))
    vmax_var = ds.createVariable("vmax_interp", vlen_f4, ("storm",))
    speed_var = ds.createVariable("speed_kmh", vlen_f4, ("storm",))
    direction_var = ds.createVariable("direction_deg", vlen_f4, ("storm",))
    vmax_change_var = ds.createVariable("vmax_change", vlen_f4, ("storm",))
    speed_change_var = ds.createVariable("speed_change", vlen_f4, ("storm",))
    direction_change_var = ds.createVariable("direction_change_deg", vlen_f4, ("storm",))
    start_ri_time_var = ds.createVariable("start_ri_time", vlen_i8, ("storm",))
    end_ri_time_var = ds.createVariable("end_ri_time", vlen_i8, ("storm",))
    intensities_var = ds.createVariable("intensities", vlen_f4, ("storm",))

    for i in range(len(out_storm_ids)):
        storm_id_var[i] = out_storm_ids[i]
        storm_name_var[i] = out_storm_names[i]
        storm_hemisphere_var[i] = out_hemisphere[i]
        storm_initial_vmax_var[i] = out_vmax_initial[i]
        storm_final_vmax_var[i] = out_vmax_final[i]
        times_var[i] = out_times[i]
        lat_var[i] = out_lats[i]
        lon_var[i] = out_lons[i]
        vmax_var[i] = out_vmaxs[i]
        speed_var[i] = out_speed_kmh[i]
        direction_var[i] = out_direction_deg[i]
        vmax_change_var[i] = out_vmax_change[i]
        speed_change_var[i] = out_speed_change[i]
        direction_change_var[i] = out_direction_change_deg[i]
        start_ri_time_var[i] = np.array([out_start_ri_time[i]], dtype=np.int64)
        end_ri_time_var[i] = np.array([out_end_ri_time[i]], dtype=np.int64)
        intensities_var[i] = np.array([out_intensities[i]], dtype=np.float32)

    # variable metadata
    times_var.units = "seconds since 1970-01-01T00:00:00"
    times_var.long_name = "interpolated time"

    lat_var.units = "degrees_north"
    lat_var.long_name = "interpolated latitude"

    lon_var.units = "degrees_east"
    lon_var.long_name = "interpolated longitude"

    vmax_var.units = "knots"
    vmax_var.long_name = "interpolated maximum wind speed"

    speed_var.units = "km h-1"
    speed_var.long_name = "storm translation speed"

    direction_var.units = "degrees"
    direction_var.long_name = "storm motion direction"

    vmax_change_var.units = "knots hour-1"
    vmax_change_var.long_name = "rate of change of maximum wind speed"

    speed_change_var.units = "km h-2"
    speed_change_var.long_name = "rate of change of translation speed"

    direction_change_var.units = "degrees hour-1"
    direction_change_var.long_name = "rate of change of motion direction"

    storm_id_var.long_name = "storm identifier"
    storm_name_var.long_name = "storm name"

    # global metadata
    ds.title = "Interpolated RI storm tracks"
    ds.institution = "RMIT University"
    ds.source = "IBTrACS RI events"
    ds.history = "Created from c_interpolate_storms.py"
    ds.interp_time_minutes = interp_time
    ds.spline_interp_order = spline_interp_order
    ds.compare_interp = int(compare_interp)
