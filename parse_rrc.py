import csv
import os
from collections import defaultdict

# --- Configuration ---
INPUT_DAT_FILE = 'data/raw/daf420.dat.06-30-2025'
OUTPUT_DIR = 'raw/rrc_output'
RECORD_LENGTH = 510

# ==============================================================================
# RECORD LAYOUTS (MAPPING) FROM THE RRC MANUAL - EXPANDED AND CORRECTED
# Note: All positions are 0-indexed (Position 1 in manual is index 0 here)
# ==============================================================================

RECORD_MAPS = {
    # Record ID '01': DA-STATUS-ROOT (Page II.2)
    '01': [
        ('RRC_TAPE_RECORD_ID', 0, 2),
        ('DA_STATUS_NUMBER', 2, 7),
        ('DA_STATUS_SEQUENCE_NUMBER', 9, 2),
        ('DA_COUNTY_CODE_ROOT', 11, 3),
        ('DA_LEASE_NAME_ROOT', 14, 32),
        ('DA_DISTRICT_ROOT', 46, 2),
        ('DA_OPERATOR_NUMBER_ROOT', 48, 6),
        ('DA_DATE_APP_RECEIVED', 58, 8),
        ('DA_OPERATOR_NAME', 66, 32),
        ('DA_STATUS_OF_APP_FLAG', 100, 1),
        ('DA_PERMIT_ROOT', 112, 7),
        ('DA_ISSUE_DATE', 119, 8),
        ('DA_WELL_NUMBER_ROOT', 156, 6),
        ('DA_ECAP_FILING_FLAG', 182, 1),
    ],
    # Record ID '02': DA-PERMIT-MASTER (Page II.14)
    '02': [
        ('DA_PERMIT_NUMBER', 4, 7),
        ('DA_PERMIT_SEQUENCE_NUMBER', 11, 2),
        ('DA_PERMIT_COUNTY_CODE', 13, 3),
        ('DA_PERMIT_LEASE_NAME', 16, 32),
        ('DA_PERMIT_DISTRICT', 48, 2),
        ('DA_PERMIT_WELL_NUMBER', 50, 6),
        ('DA_PERMIT_TOTAL_DEPTH', 56, 5),
        ('DA_PERMIT_OPERATOR_NUMBER', 61, 6),
        ('DA_TYPE_APPLICATION', 67, 2),
        ('DA_RECEIVED_DATE', 123, 8),
        ('DA_PERMIT_ISSUED_DATE', 131, 8),
        ('DA_WELL_STATUS', 171, 1),
        ('DA_RULE_37_CASE_NUMBER', 230, 7),
        ('DA_OLD_SURFACE_LOCATION', 245, 52),
        ('DA_SURFACE_ACRES', 327, 8), # PIC 9(06)V9(2)
        ('DA_SURFACE_MILES_FROM_CITY', 335, 6), # PIC 9(04)V9(2)
        ('DA_SURFACE_DIRECTION_FROM_CITY', 341, 6),
        ('DA_SURFACE_NEAREST_CITY', 347, 13),
        ('DA_NEAREST_WELL', 444, 28),
        ('DA_DIRECTIONAL_WELL_FLAG', 483, 1),
        ('DA_HORIZONTAL_WELL_FLAG', 495, 1),
        ('API_NUMBER', 504, 8),
    ],
    # Record ID '03': DA-FIELD-SEGMENT (Page II.33)
    '03': [
        ('DA_FIELD_NUMBER', 2, 8),
        ('DA_FIELD_APPLICATION_WELL_CODE', 10, 1),
        ('DA_FIELD_COMPLETION_WELL_CODE', 11, 1),
        ('DA_FIELD_COMPLETION_DATE', 22, 8),
    ],
    # Record ID '06': DA-CAN-RESTR-SEGMENT (Page II.47)
    '06': [
        ('DA_CAN_RESTR_KEY', 2, 2),
        ('DA_CAN_RESTR_TYPE', 4, 2),
        ('DA_CAN_RESTR_REMARK', 6, 35),
        ('DA_CAN_RESTR_FLAG', 76, 1),
    ],
    # Record ID '08': DA-FREE-RESTR-SEGMENT (Page II.58)
    '08': [
        ('DA_FREE_RESTR_KEY', 2, 2),
        ('DA_FREE_RESTR_REMARK', 6, 70),
        ('DA_FREE_RESTR_FLAG', 76, 1),
    ],
    # Record ID '14': GIS SURFACE LOCATION (Page II.75)
    '14': [
        ('SURFACE_LONGITUDE', 3, 12),
        ('SURFACE_LATITUDE', 15, 12),
    ],
    # Record ID '15': GIS BOTTOM HOLE LOCATION (Page II.77)
    '15': [
        ('BH_LONGITUDE', 3, 12),
        ('BH_LATITUDE', 15, 12),
    ],
}

def parse_line(line, record_map):
    """Parses a single fixed-width line based on the provided map."""
    record_data = {}
    for name, start, length in record_map:
        value = line[start : start + length].strip()
        record_data[name] = value
    return record_data

def format_implied_decimal(value, integer_part_len):
    """Converts a string with an implied decimal into a proper float string."""
    if not value or not value.replace('-', '').replace('.', '').isdigit():
        return value

    is_negative = value.startswith('-')
    if is_negative:
        value = value[1:]
    
    if len(value) <= integer_part_len:
        formatted_value = value
    else:
        formatted_value = f"{value[:integer_part_len]}.{value[integer_part_len:]}"

    return f"-{formatted_value}" if is_negative else formatted_value

def process_file():
    """Main function to orchestrate the file parsing and writing."""
    if not os.path.exists(INPUT_DAT_FILE):
        print(f"Error: Input file '{INPUT_DAT_FILE}' not found.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output will be saved in '{OUTPUT_DIR}' directory.")

    permits = []
    all_fields = []
    all_restrictions = []
    
    current_permit_data = {}
    line_num = 0
    record_counts = defaultdict(int)

    print(f"Processing '{INPUT_DAT_FILE}'...")
    with open(INPUT_DAT_FILE, 'r', encoding='latin-1') as f_in:
        for line in f_in:
            line_num += 1
            if len(line.strip()) == 0: continue
            line = line.rstrip('\n').ljust(RECORD_LENGTH, ' ')
            
            record_id = line[0:2]
            record_counts[record_id] += 1

            if record_id == '01':
                if current_permit_data:
                    permits.append(current_permit_data)
                current_permit_data = parse_line(line, RECORD_MAPS['01'])
                
            elif current_permit_data:
                record_map = RECORD_MAPS.get(record_id)
                if not record_map: continue

                if record_id == '02':
                    permit_master_data = parse_line(line, record_map)
                    permit_master_data['DA_SURFACE_ACRES'] = format_implied_decimal(permit_master_data.get('DA_SURFACE_ACRES', ''), 6)
                    permit_master_data['DA_SURFACE_MILES_FROM_CITY'] = format_implied_decimal(permit_master_data.get('DA_SURFACE_MILES_FROM_CITY', ''), 4)
                    current_permit_data.update(permit_master_data)
                
                elif record_id == '03':
                    field_data = parse_line(line, record_map)
                    field_data['PARENT_STATUS_NUMBER'] = current_permit_data.get('DA_STATUS_NUMBER')
                    all_fields.append(field_data)
                    
                elif record_id in ['06', '08']:
                    restriction_data = parse_line(line, record_map)
                    restriction_data['PARENT_STATUS_NUMBER'] = current_permit_data.get('DA_STATUS_NUMBER')
                    restriction_data['RESTRICTION_TYPE'] = 'CANNED' if record_id == '06' else 'FREE_FORM'
                    all_restrictions.append(restriction_data)
                
                elif record_id == '14':
                    gis_data = parse_line(line, record_map)
                    current_permit_data['SURFACE_LATITUDE'] = format_implied_decimal(gis_data.get('SURFACE_LATITUDE', ''), 2)
                    current_permit_data['SURFACE_LONGITUDE'] = format_implied_decimal(gis_data.get('SURFACE_LONGITUDE', ''), 3)
                    
                elif record_id == '15':
                    gis_data = parse_line(line, record_map)
                    current_permit_data['BH_LATITUDE'] = format_implied_decimal(gis_data.get('BH_LATITUDE', ''), 2)
                    current_permit_data['BH_LONGITUDE'] = format_implied_decimal(gis_data.get('BH_LONGITUDE', ''), 3)

    if current_permit_data:
        permits.append(current_permit_data)

    # --- Write Output Files ---
    permits_csv_path = os.path.join(OUTPUT_DIR, 'permits.csv')
    if permits:
        permit_headers = sorted(list(set(key for p_data in permits for key in p_data.keys())))
        with open(permits_csv_path, 'w', newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=permit_headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(permits)
        print(f"Wrote {len(permits)} permits to '{permits_csv_path}'")

    fields_csv_path = os.path.join(OUTPUT_DIR, 'permit_fields.csv')
    if all_fields:
        # CORRECTED: Gather keys from ALL field records, not just the first one.
        all_field_keys = set(key for field in all_fields for key in field.keys())
        field_headers = sorted(list(all_field_keys))
        with open(fields_csv_path, 'w', newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=field_headers)
            writer.writeheader()
            writer.writerows(all_fields)
        print(f"Wrote {len(all_fields)} fields to '{fields_csv_path}'")
        
    restrictions_csv_path = os.path.join(OUTPUT_DIR, 'permit_restrictions.csv')
    if all_restrictions:
        # CORRECTED: Gather keys from ALL restriction records to handle different types.
        all_res_keys = set(key for res in all_restrictions for key in res.keys())
        res_headers = sorted(list(all_res_keys))
        with open(restrictions_csv_path, 'w', newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=res_headers)
            writer.writeheader()
            writer.writerows(all_restrictions)
        print(f"Wrote {len(all_restrictions)} restrictions to '{restrictions_csv_path}'")

    print("\n--- Processing Summary ---")
    print(f"Total lines processed: {line_num}")
    for rec_id, count in sorted(record_counts.items()):
        print(f"Record Type '{rec_id}': {count} occurrences")
    print("--------------------------\nProcessing complete.")

if __name__ == '__main__':
    process_file()