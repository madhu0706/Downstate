import os
import numpy as np
import sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, "/data/downstate/ez-detect/src")
print("Updated Python module search paths:", sys.path)

from evtio.evtio.io import EventFile, write_evt, load_events_from_matfiles
import scipy.io
import mne
from trcio import read_raw_trc
import argparse

# Fix the start and end time for events
FIXED_START_TIME = datetime(1910, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
FIXED_CREATION_DATE = FIXED_START_TIME  # Set the creation date to the fixed start time

def create_event_file(trc_filepath, output_dir):
    """Creates an event file from TRC and MAT files."""

    evt_fname = os.path.join(output_dir, "test_events.EVT")

    # Load TRC file
    print(f"Loading TRC file: {trc_filepath}")
    try:
        raw_trc = read_raw_trc(trc_filepath)
        print(f"TRC file loaded successfully: {trc_filepath}")
    except FileNotFoundError:
        print(f"Error: TRC file not found at {trc_filepath}")
        return
    except Exception as e:
        print(f"Error loading TRC file: {e}")
        return

    # Automatically load all MAT files from the specified directories
    mat_file_paths = []
    mat_directories = [
        "/data/downstate/ez-detect/disk_dumps/ez_top/output/",
        "/data/downstate/ez-detect/disk_dumps/ez_pac_output/"
    ]
    
    for directory in mat_directories:
        try:
            mat_files = [f for f in os.listdir(directory) if f.endswith('.mat')]
            mat_file_paths.extend([os.path.join(directory, f) for f in mat_files])
            print(f"Found {len(mat_files)} MAT files in {directory}")
        except FileNotFoundError:
            print(f"Error: Directory not found: {directory}")
            return
        except Exception as e:
            print(f"Error accessing directory {directory}: {e}")
            return

    if not mat_file_paths:
        print("Error: No MAT files found in the specified directories.")
        return

    # Load events from all the MAT files found
    all_events = set()

    rec_start_time = FIXED_START_TIME  # Set the fixed start time
    print(f"Using fixed start time: {rec_start_time}")

    for mat_filepath in mat_file_paths:
        print(f"Loading MAT file: {mat_filepath}")
        try:
            matfile_vars = scipy.io.loadmat(mat_filepath)
            metadata = matfile_vars['metadata'][0][0]
            first_montage = metadata['montage'][0]  # Extract the montage structure
            
            events = load_events_from_matfiles(
                os.path.dirname(mat_filepath),
                raw_trc.info['ch_names'],
                first_montage,
                rec_start_time,
            )
            all_events.update(events)
            print(f"Events loaded successfully from {mat_filepath}")
        except FileNotFoundError:
            print(f"Error: MAT file not found at {mat_filepath}")
        except KeyError as e:
            print(f"Error accessing key in MAT file: {e}. Check if the file has the correct structure.")
        except Exception as e:
            print(f"Error loading MAT file {mat_filepath}: {e}")

    # Create and write the EVT file
    print(f"Total number of events: {len(all_events)}")

    try:
        # Create the event file with the fixed CreationDate
        evt_file = EventFile(evt_fname, FIXED_CREATION_DATE, events=all_events, username='TESTUSER')
        write_evt(evt_file)
        print(f"EVT file created successfully at: {evt_fname}")
    except Exception as e:
        print(f"Error writing EVT file: {e}")
        return

# Function to format the time for the XML output
def format_time_for_xml(datetime_obj):
    return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S") + ".0000000"

if __name__ == "__main__":
    print(f"Current working directory: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print(f"sys.path: {sys.path}")

    parser = argparse.ArgumentParser(description="Create event file from TRC and MAT files.")
    parser.add_argument("trc_file", help="Path to the TRC file.")
    parser.add_argument("output_dir", help="Directory to save the output EVT file.")
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        print(f"Error: The specified output directory does not exist: {args.output_dir}")
        sys.exit(1)

    create_event_file(args.trc_file, args.output_dir)

