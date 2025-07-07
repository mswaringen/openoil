import csv
import math
import os
from pyproj import Transformer, CRS

# --- Configuration ---
INPUT_PERMITS_CSV = os.path.join('data/rrc_output', 'permits.csv')
OUTPUT_AOI_CSV = os.path.join('data/rrc_output', 'well_aoi_for_imagery.csv')

# Define the Coordinate Reference Systems (CRS)
# NAD27 Geographic coordinates (latitude, longitude)
CRS_NAD27 = CRS("EPSG:4267")
# WGS 84 Geographic coordinates (the standard for GPS/satellite)
CRS_WGS84 = CRS("EPSG:4326")

# Create a transformer object to convert from NAD27 to WGS 84
# The 'always_xy=True' argument ensures order is always (longitude, latitude)
transformer = Transformer.from_crs(CRS_NAD27, CRS_WGS84, always_xy=True)

def convert_nad27_to_wgs84(lon_nad27, lat_nad27):
    """
    Converts a single NAD27 coordinate pair to WGS 84.
    """
    # pyproj transformer expects (longitude, latitude)
    lon_wgs84, lat_wgs84 = transformer.transform(lon_nad27, lat_nad27)
    return lat_wgs84, lon_wgs84

def calculate_wgs84_bounding_box(center_lat, center_lon, distance_ft):
    """
    Calculates the WGS 84 bounding box coordinates around a center point.
    """
    FEET_PER_DEGREE_LAT = 364000
    lat_offset_deg = distance_ft / FEET_PER_DEGREE_LAT
    
    feet_per_deg_lon = FEET_PER_DEGREE_LAT * math.cos(math.radians(center_lat))
    # Handle potential division by zero at the poles, though unlikely for Texas
    if feet_per_deg_lon == 0:
        lon_offset_deg = 0
    else:
        lon_offset_deg = distance_ft / feet_per_deg_lon

    return {
        'min_lat_wgs84': center_lat - lat_offset_deg,
        'max_lat_wgs84': center_lat + lat_offset_deg,
        'min_lon_wgs84': center_lon - lon_offset_deg,
        'max_lon_wgs84': center_lon + lon_offset_deg,
    }

def main():
    """
    Reads permits, converts coordinates, calculates bounding boxes, and writes output.
    """
    if not os.path.exists(INPUT_PERMITS_CSV):
        print(f"Error: Input file '{INPUT_PERMITS_CSV}' not found.")
        print("Please run the initial parsing script first.")
        return

    # Define the size of the desired imagery area
    # A 500x500 foot box is a safe bet for most well pads
    box_side_length_ft = 500
    box_half_width_ft = box_side_length_ft / 2
    total_area_acres = (box_side_length_ft ** 2) / 43560

    print(f"Processing '{INPUT_PERMITS_CSV}'...")
    print(f"Defining a {box_side_length_ft}x{box_side_length_ft} ft AOI ({total_area_acres:.2f} acres) for each well.")

    output_rows = []
    processed_count = 0
    error_count = 0

    with open(INPUT_PERMITS_CSV, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            try:
                # Get the raw NAD27 coordinates from the parsed file
                lat_nad27_str = row.get('SURFACE_LATITUDE')
                lon_nad27_str = row.get('SURFACE_LONGITUDE')

                # Skip rows with no coordinate data
                if not lat_nad27_str or not lon_nad27_str:
                    continue

                lat_nad27 = float(lat_nad27_str)
                lon_nad27 = float(lon_nad27_str)

                # --- Step 1: Convert to WGS 84 ---
                lat_wgs84, lon_wgs84 = convert_nad27_to_wgs84(lon_nad27, lat_nad27)

                # --- Step 2: Calculate Bounding Box using WGS 84 coordinates ---
                bbox_wgs84 = calculate_wgs84_bounding_box(lat_wgs84, lon_wgs84, box_half_width_ft)
                
                # Prepare the output row
                output_row = {
                    'API_NUMBER': row.get('API_NUMBER'),
                    'DA_STATUS_NUMBER': row.get('DA_STATUS_NUMBER'),
                    'OPERATOR_NAME': row.get('DA_OPERATOR_NAME'),
                    'LEASE_NAME': row.get('DA_PERMIT_LEASE_NAME'),
                    'center_lat_wgs84': f"{lat_wgs84:.6f}",
                    'center_lon_wgs84': f"{lon_wgs84:.6f}",
                    **bbox_wgs84 # Unpack the bounding box dictionary into the row
                }
                output_rows.append(output_row)
                processed_count += 1

            except (ValueError, TypeError):
                # This catches errors if coordinates are not valid numbers
                error_count += 1
                continue

    # --- Step 3: Write the final CSV ---
    if output_rows:
        print(f"\nSuccessfully processed {processed_count} wells.")
        if error_count > 0:
            print(f"Skipped {error_count} rows due to invalid coordinate data.")
        
        # Ensure all keys are present for the header
        header = list(output_rows[0].keys())
        
        with open(OUTPUT_AOI_CSV, 'w', newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=header)
            writer.writeheader()
            writer.writerows(output_rows)
        
        print(f"\nSuccess! Wrote final Area of Interest data to '{OUTPUT_AOI_CSV}'")
        print("This is the file you should provide to your satellite imagery provider.")
    else:
        print("No wells with valid coordinates found to process.")


if __name__ == '__main__':
    main()