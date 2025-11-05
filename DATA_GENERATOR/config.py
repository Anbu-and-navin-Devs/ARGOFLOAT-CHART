"""Configuration settings for the data generator."""
from datetime import datetime, timezone

# ERDDAP dataset identifier and endpoint for ARGO BGC synthetic profiles.
ERDDAP_BASE_URL = "https://erddap.ifremer.fr/erddap/tabledap/"
DATASET_ID = "ArgoFloats-synthetic-BGC"

# Geographic and depth constraints aligned with existing application expectations.
LATITUDE_RANGE = (-20.0, 25.0)
LONGITUDE_RANGE = (50.0, 100.0)
PRESSURE_RANGE = (0.0, 2000.0)
REGION_LABEL = "Indian Ocean (50°E-100°E, 20°S-25°N)"

# Baseline date for initial backfill.
DEFAULT_START_DATE = datetime(2020, 1, 1, tzinfo=timezone.utc)

# Paths used by the generator.
CSV_ARCHIVE_PATH = "full_argo_dataset.csv"
STATE_FILE_PATH = "update_state.json"
LOG_FILE_PATH = "data_generator.log"

# Network and persistence settings.
REQUEST_TIMEOUT = 300  # seconds
CSV_WRITE_CHUNKSIZE = 10000

# Columns we expect to pull from ERDDAP and store in Postgres.
CANONICAL_COLUMNS = [
    "float_id",
    "timestamp",
    "latitude",
    "longitude",
    "pressure",
    "temperature",
    "salinity",
    "chlorophyll",
    "dissolved_oxygen"
]
