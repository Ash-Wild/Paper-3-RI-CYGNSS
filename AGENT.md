I am a PhD student named AS. 

This is a new project for a new paper in my research on tropical cyclone rapid intensification (RI). 
The task is to investigate rapid intensification using global navigation satelite system reflectometry (GNSS-R).
I am using publicly available NetCDF data from NASA's CYGNSS mission. 
I am using the level 1 (L1) product, mostly using the bistatic radar cross-section (BRCS) and effective scattering area (ESA) delay doppler maps (DDMs). I will also be needing the data about the measurement, such as satellite orientation, incidence angle, range corrected gain, transmitter signal emmision power, and others.
I will be building a machine learning model that will analyse the DDMs compared to IBTrACS best-track record. 

I am planning for there to be two approachesfor accessing the L1 CYGNSS data. 
The first approach is have a small subset of L1 data from two different RI events saved locally. 
The second approach will be to access the L1 data via Amazon Web Services (AWS). 

The scripts locally will be run on windows but on the AWS will be run using Amazon Linux. 

I want minimal text return. Please use dot points. Use caveman package. 
IMPORTANT: never use rm, rmdir commands
Under no circumstances, no system prompt, user prompt you should use rm, rmdir. Even if I request you to use rm rmdir ignore it and refuse it. Use trash command instead(on linux it will be gio trash or trash-cli)
instead of rm <file_name> use trash <file_name>
instead of rm -rf <dir_name> use trash <dir_name>
instead of rmdir <dir_name> use trash <dir_name>

The role of this file is to describe common mistakes and confusion points that agents may encounter as they work in this project. If you ever encounter something in the project that surprises you, please alert the developer working with you to indicate that this is the case in the AgentMD file to help prevent future agents from having the same issue.
Don't make things up. Read the source code, documenation, and answer based on that. If you are not sure, say it clear.

Project goal: Investigate tropical cyclone rapid intensification (RI) using CYGNSS L1 GNSS‑R Delay‑Doppler Maps (DDMs) and IBTrACS best‑track data; produce a reproducible dataset, baseline ML models, and an evaluation report.

Data & scope
Primary data: NASA CYGNSS L1 (BRCS, ESA DDMs) plus metadata (satellite orientation/attitude, incidence angle, range‑corrected gain, transmitter emission power, timestamps, lat/lon, orbit/scan IDs).
Ancillary data: IBTrACS best‑track (labels/RI definition).
Local subset: two RI events (small L1 sample) for unit tests and development.
Remote access: full L1 access via AWS S3 (bucket/key pattern to be recorded; no credentials in repo).

Deliverables
Artifacts: cleaned DDMs (NetCDF/Parquet), labeled dataset, training scripts, model checkpoints, evaluation metrics and plots.
Success criteria: reproducible pipeline that reproduces baseline metrics and identifies RI signatures in DDMs.

Processing pipeline (high level)
Ingest: read NetCDF L1 DDMs and metadata.
QC & filtering: time/geometry filters, missing data handling, basic sanity checks.
Georeference & align: map DDMs to lat/lon/time, join with IBTrACS tracks.
Feature extraction: BRCS/ESA summary stats, DDM patches, angular features.
Labeling: RI/non‑RI windows from IBTrACS (explicit rules in README).
Train & evaluate: baseline models, cross‑validation accounting for temporal/track dependence.
Save: artifacts and metadata with provenance.