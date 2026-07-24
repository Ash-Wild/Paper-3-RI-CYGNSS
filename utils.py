def haversine_km(lat1, lon1, lat2, lon2):
    import numpy as np
    r = 6371.0
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return r * c

def haversine_vectorized(latlon1, latlon2):
    """
    Compute the great-circle distance between two sets of (lat, lon) coordinates using vectorized operations.
    """
    import numpy as np

    R = 6371.0  # Earth radius in km
    lat1, lon1 = np.radians(latlon1[:, 0]), np.radians(latlon1[:, 1])
    lat2, lon2 = np.radians(latlon2[:, 0]), np.radians(latlon2[:, 1])
    dlat = lat2[:, None] - lat1[None, :]
    dlon = lon2[:, None] - lon1[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1[None, :]) * np.cos(lat2[:, None]) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return (R * c).T  # Transpose to match expected shape


def angle_deg(lat1, lon1, lat2, lon2):
    import numpy as np
    return (np.degrees(np.arctan2(lat2 - lat1, lon2 - lon1)) + 360) % 360


def nearest_storm_point(obs_time_s, obs_lat, obs_lon, storm_times, storm_lats, storm_lons):
    import numpy as np
    time_diffs = np.abs(storm_times - obs_time_s)
    idx = int(np.argmin(time_diffs))
    time_delta_minutes = time_diffs[idx] / 60.0
    distance_km = haversine_km(obs_lat, obs_lon, storm_lats[idx], storm_lons[idx])
    return idx, time_delta_minutes, distance_km


def match_observation_to_storm(obs_time_s, obs_lat, obs_lon, storm_times, storm_lats, storm_lons):
    idx, time_delta_minutes, distance_km = nearest_storm_point(
        obs_time_s, obs_lat, obs_lon, storm_times, storm_lats, storm_lons
    )
    from a_config import cyg_time_from_storm, cyg_dist_from_storm
    
    if time_delta_minutes > cyg_time_from_storm:
        return None
    if distance_km > cyg_dist_from_storm:
        return None

    return {
        "obs_time": obs_time_s,
        "obs_lat": obs_lat,
        "obs_lon": obs_lon,
        "storm_index": idx,
        "storm_time": storm_times[idx],
        "storm_lat": storm_lats[idx],
        "storm_lon": storm_lons[idx],
        "time_delta_minutes": time_delta_minutes,
        "distance_km": distance_km,
    }

def get_cygnss_files(temporal):
    import os, glob
    from datetime import datetime
    from a_config import data_dir, test_folder

    start_time, end_time = temporal
    cygnss_files = []

    current_time = start_time
    while current_time <= end_time:
        date_str = datetime.utcfromtimestamp(current_time).strftime("%Y%m%d")
        cygnss_file_path = os.path.join(data_dir + test_folder, f"*{date_str}-235959.l1.power-brcs.a32.d33.nc")
        cygnss_file_path = glob.glob(cygnss_file_path)
        if cygnss_file_path:
            cygnss_files.extend(cygnss_file_path)

        current_time += 24 * 3600  # increment by one day

    return cygnss_files

def find_valid_cygnss_indices(cyg_times, cyg_lats, cyg_lons, storm_times, storm_lats, storm_lons, lat_min, lat_max, lon_min, lon_max, cyg_dist_from_storm, cyg_time_from_storm):
    from utils import haversine_vectorized
    import numpy as np
    from datetime import datetime

    # create a mask to filter the cygnss data to only include points within the lat/lon bounds of the storm plus the buffer
    spatial_mask = (
        (cyg_lats >= lat_min) &
        (cyg_lats <= lat_max) &
        (cyg_lons >= lon_min) &
        (cyg_lons <= lon_max)
    )

    cyg_times = cyg_times[spatial_mask]
    cyg_lats = cyg_lats[spatial_mask]
    cyg_lons = cyg_lons[spatial_mask]

    cyg_coords = np.column_stack((cyg_lats, cyg_lons))
    storm_coords = np.column_stack((storm_lats, storm_lons))

    if len(cyg_times) == 0:
        return None, None, None

    distances = haversine_vectorized(cyg_coords, storm_coords)
    time_diffs = np.abs(cyg_times[:, None] - storm_times[None, :]) / 60 # minutes
    valid_mask = (distances <= cyg_dist_from_storm) & (time_diffs <= cyg_time_from_storm)
    valid_idx = np.where(valid_mask)  

    return spatial_mask, valid_idx, distances[valid_idx],time_diffs[valid_idx] 

def quadrant_from_storm(cyg_lats_valid, cyg_lons_valid, storm_lats_i, storm_lons_i, tc_indices, storm_directions_i, storm_hemisphere_i):
    import numpy as np

    storm_lats_i = np.asarray(storm_lats_i)
    storm_lons_i = np.asarray(storm_lons_i)
    storm_directions_i = np.asarray(storm_directions_i)

    tc_indices = np.asarray(tc_indices, dtype=int)
    tc_indices = np.clip(tc_indices, 0, len(storm_lats_i) - 1)

    rel_x = np.asarray(cyg_lons_valid) - storm_lons_i[tc_indices]
    rel_y = np.asarray(cyg_lats_valid) - storm_lats_i[tc_indices]

    tc_heading_rad = np.radians(storm_directions_i[tc_indices])
    rot_x = rel_x * np.cos(tc_heading_rad) + rel_y * np.sin(tc_heading_rad)
    rot_y = -rel_x * np.sin(tc_heading_rad) + rel_y * np.cos(tc_heading_rad)

    quadrants = np.full(rot_x.shape, "Unknown", dtype=object)
    quadrants[(rot_x >= 0) & (rot_y >= 0)] = "Front-Left"
    quadrants[(rot_x >= 0) & (rot_y < 0)] = "Front-Right"
    quadrants[(rot_x < 0) & (rot_y >= 0)] = "Rear-Left"
    quadrants[(rot_x < 0) & (rot_y < 0)] = "Rear-Right"

    if storm_hemisphere_i == "Southern":
        quadrants = np.where(quadrants == "Front-Left", "Front-Right", quadrants)
        quadrants = np.where(quadrants == "Rear-Left", "Rear-Right", quadrants)
        quadrants = np.where(quadrants == "Front-Right", "Front-Left", quadrants)
        quadrants = np.where(quadrants == "Rear-Right", "Rear-Left", quadrants)

    if storm_hemisphere_i == "Northern":
        cyg_direction = (np.degrees(np.arctan2(rel_y, rel_x)) + 360) % 360
    else:
        cyg_direction = (np.degrees(np.arctan2(-rel_y, rel_x)) + 360) % 360

    return quadrants, cyg_direction

# create an animation of the storm's movement and intensity over time, with the interpolated points and the rate of change of the storm's direction, speed, and intensity displayed on the animation. The direction of the storm's movement will be represented by an arrow, the speed of the storm will be represented by the length of the arrow, and the intensity of the storm will be represented by the color of the arrow. The rate of change of the storm's direction, speed, and intensity will be represented by three vertical bars displayed on the animation.
def make_animation(
    storm_times_interp,
    storm_lats_interp,
    storm_lons_interp,
    storm_vmaxs_interp,
    storm_speed_kmh,
    storm_direction_deg,
    storm_vmax_change,
    storm_speed_change,
    storm_direction_change_deg,
    storm_id,
    storm_name
):
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from matplotlib.colors import Normalize
    import numpy as np

    storm_lats_interp = np.asarray(storm_lats_interp)
    storm_lons_interp = np.asarray(storm_lons_interp)
    storm_vmaxs_interp = np.asarray(storm_vmaxs_interp)
    storm_speed_kmh = np.asarray(storm_speed_kmh)
    storm_direction_deg = np.asarray(storm_direction_deg)
    storm_vmax_change = np.asarray(storm_vmax_change)
    storm_speed_change = np.asarray(storm_speed_change)
    storm_direction_change_deg = np.asarray(storm_direction_change_deg)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(np.min(storm_lons_interp) - 1, np.max(storm_lons_interp) + 1)
    ax.set_ylim(np.min(storm_lats_interp) - 1, np.max(storm_lats_interp) + 1)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"{storm_name} (ID: {storm_id})")

    ax.plot(storm_lons_interp, storm_lats_interp, color="lightgray", lw=1, alpha=0.7)
    point, = ax.plot([], [], "o", color="black", markersize=5)

    norm = Normalize(vmin=np.min(storm_vmaxs_interp), vmax=np.max(storm_vmaxs_interp))
    cmap = plt.cm.viridis

    lon_span = np.max(storm_lons_interp) - np.min(storm_lons_interp)
    lat_span = np.max(storm_lats_interp) - np.min(storm_lats_interp)
    arrow_scale = 0.08 * max(lon_span, lat_span) / max(np.max(storm_speed_kmh), 1e-6)

    q = ax.quiver(
        [storm_lons_interp[0]],
        [storm_lats_interp[0]],
        [0],
        [0],
        angles="xy",
        scale_units="xy",
        scale=1,
        color=[cmap(norm(storm_vmaxs_interp[0]))]
    )
    bar_ax = ax.inset_axes([0.72, 0.58, 0.25, 0.32])
    bar_labels = ["Dir", "Speed", "Vmax"]
    bar_x = np.arange(len(bar_labels))
    bar_colors = ["tab:blue", "tab:orange", "tab:green"]
    bar_vals = [
        storm_direction_change_deg[0] if len(storm_direction_change_deg) else 0,
        storm_speed_change[0] if len(storm_speed_change) else 0,
        storm_vmax_change[0] if len(storm_vmax_change) else 0,
    ]

    bars = bar_ax.bar(bar_x, bar_vals, color=bar_colors, align="center")
    bar_ax.set_xticks(bar_x)
    bar_ax.set_xticklabels(bar_labels)
    bar_ax.set_title("Rate of change")
    bar_ax.axhline(0, color="black", lw=0.8)

    max_abs = max(
        float(np.max(np.abs(storm_direction_change_deg))) if len(storm_direction_change_deg) else 1.0,
        float(np.max(np.abs(storm_speed_change))) if len(storm_speed_change) else 1.0,
        float(np.max(np.abs(storm_vmax_change))) if len(storm_vmax_change) else 1.0,
        1.0
    )
    bar_ax.set_ylim(-max_abs * 1.1, max_abs * 1.1)

    def init():
        point.set_data([], [])
        q.set_offsets([[storm_lons_interp[0], storm_lats_interp[0]]])
        q.set_UVC([0], [0])
        q.set_color([cmap(norm(storm_vmaxs_interp[0]))])

        init_vals = [
            storm_direction_change_deg[0] if len(storm_direction_change_deg) else 0,
            storm_speed_change[0] if len(storm_speed_change) else 0,
            storm_vmax_change[0] if len(storm_vmax_change) else 0,
        ]
        for bar, val in zip(bars, init_vals):
            bar.set_height(val)

        return point, q, *bars

    def update(frame):
        x = storm_lons_interp[frame]
        y = storm_lats_interp[frame]

        angle = np.radians(storm_direction_deg[frame])
        speed = storm_speed_kmh[frame] * arrow_scale
        u = speed * np.cos(angle)
        v = speed * np.sin(angle)

        point.set_data([x], [y])
        q.set_offsets([[x, y]])
        q.set_UVC([u], [v])
        q.set_color([cmap(norm(storm_vmaxs_interp[frame]))])

        vals = [
            storm_direction_change_deg[frame],
            storm_speed_change[frame],
            storm_vmax_change[frame],
        ]
        for bar, val in zip(bars, vals):
            bar.set_height(val)
            bar.set_color(bar.get_facecolor())

        return point, q, *bars

    ani = FuncAnimation(
        fig,
        update,
        frames=len(storm_times_interp),
        init_func=init,
        interval=50,
        blit=False,
        repeat=False
    )

    plt.show()

def create_storm_animation(storm_id, storm_name, storm_times, storm_lats, storm_lons, storm_vmaxs, storm_directions, dataframe, cyg_times, cyg_lats, cyg_lons):

    # function takes interpolated storm data and the pandas dataframe from file d_cygnss_matchups.py as input. It creates an animation of the storm's movement and intensity over time as well as the CYGNSS measurements that are matched to the storm. The direction of the storm's movement will be represented by an arrow, and the CYGNSS measurements will be represented by points on the map. The color of the arrow will represent the intensity of the storm, and the colour of the points will represent the direction relative to the storm's movement. The symbol of the points will represent the quadrant relative to the storm's movement. Each point will appear on the map for 3 hours before disappearing.
    
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from matplotlib.colors import Normalize

    required_cols = {"cyg_direction", "cyg_quadrant"}
    missing_cols = required_cols - set(dataframe.columns)
    if missing_cols:
        missing_str = ", ".join(sorted(missing_cols))
        raise ValueError(f"dataframe is missing required columns: {missing_str}")

    storm_times = np.asarray(storm_times)
    storm_lats = np.asarray(storm_lats)
    storm_lons = np.asarray(storm_lons)
    storm_vmaxs = np.asarray(storm_vmaxs)
    storm_directions = np.asarray(storm_directions)

    df = dataframe.copy()

    storm_times = storm_times.astype(float)
    df["cyg_time"] = cyg_times
    df["cyg_lat"] = cyg_lats
    df["cyg_lon"] = cyg_lons

    # check if cyg_times and storm_times are similar values, 
    min_time_diff = np.min(np.abs(np.nanmean(cyg_times) - np.nanmean(storm_times))) / 3600.0
    if min_time_diff > 24.0:
        raise ValueError(f"cyg_times and storm_times are not similar values. Min time difference is {min_time_diff:.2f} hours.")


    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(np.nanmin(storm_lons) - 1, np.nanmax(storm_lons) + 1)
    ax.set_ylim(np.nanmin(storm_lats) - 1, np.nanmax(storm_lats) + 1)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"{storm_name} (ID: {storm_id})")

    ax.plot(storm_lons, storm_lats, color="lightgray", lw=1.2, alpha=0.8)
    track_line, = ax.plot([], [], color="black", lw=1.5, alpha=0.7)

    vmax_norm = Normalize(vmin=float(np.nanmin(storm_vmaxs)), vmax=float(np.nanmax(storm_vmaxs)))
    vmax_cmap = plt.cm.viridis

    direction_norm = Normalize(vmin=0.0, vmax=360.0)
    direction_cmap = plt.cm.hsv

    lon_span = float(np.nanmax(storm_lons) - np.nanmin(storm_lons))
    lat_span = float(np.nanmax(storm_lats) - np.nanmin(storm_lats))
    arrow_len = 0.08 * max(lon_span, lat_span, 1e-6)

    arrow = ax.quiver(
        [storm_lons[0]],
        [storm_lats[0]],
        [0.0],
        [0.0],
        angles="xy",
        scale_units="xy",
        scale=1.0,
        width=0.004,
        color=[vmax_cmap(vmax_norm(storm_vmaxs[0]))],
        zorder=4,
    )

    quadrant_markers = {
        "Front-Left": "*",
        "Front-Right": "s",
        "Rear-Left": "o",
        "Rear-Right": "D",
        "Unknown": "^",
    }

    quadrant_scatters = {}
    for quadrant_name, marker in quadrant_markers.items():
        quadrant_scatters[quadrant_name] = ax.scatter(
            [],
            [],
            s=42,
            marker=marker,
            edgecolors="black",
            linewidths=0.4,
            alpha=0.95,
            zorder=5,
            label=quadrant_name if quadrant_name != "Unknown" else None,
        )

    ax.legend(loc="upper left", frameon=True, fontsize=9)

    def init():
        track_line.set_data([], [])
        arrow.set_offsets([[storm_lons[0], storm_lats[0]]])
        arrow.set_UVC([0.0], [0.0])
        arrow.set_color([vmax_cmap(vmax_norm(storm_vmaxs[0]))])

        for scatter in quadrant_scatters.values():
            scatter.set_offsets(np.empty((0, 2)))
            scatter.set_facecolors(np.empty((0, 4)))

        return (track_line, arrow, *quadrant_scatters.values())

    def update(frame):
        current_lon = float(storm_lons[frame])
        current_lat = float(storm_lats[frame])

        track_line.set_data(storm_lons[: frame + 1], storm_lats[: frame + 1])

        heading_deg = float(storm_directions[frame])
        heading_rad = np.deg2rad(heading_deg)
        u = arrow_len * np.cos(heading_rad)
        v = arrow_len * np.sin(heading_rad)

        arrow.set_offsets([[current_lon, current_lat]])
        arrow.set_UVC([u], [v])
        arrow.set_color([vmax_cmap(vmax_norm(storm_vmaxs[frame]))])

        current_time = float(storm_times[frame])
        window_mask = (df["cyg_time"] >= current_time - 3 * 3600.0) & (df["cyg_time"] <= current_time)
        window_df = df.loc[window_mask]

        for quadrant_name, scatter in quadrant_scatters.items():
            quad_df = window_df[window_df["cyg_quadrant"] == quadrant_name]

            if len(quad_df) == 0:
                scatter.set_offsets(np.empty((0, 2)))
                scatter.set_facecolors(np.empty((0, 4)))
                continue

            offsets = quad_df[["cyg_lon", "cyg_lat"]].to_numpy()
            colors = direction_cmap(direction_norm(quad_df["cyg_direction"].to_numpy()))
            scatter.set_offsets(offsets)
            scatter.set_facecolors(colors)

        return (track_line, arrow, *quadrant_scatters.values())

    ani = FuncAnimation(
        fig,
        update,
        frames=len(storm_times),
        init_func=init,
        interval=10,
        blit=False,
        repeat=False,
    )

    plt.show()



