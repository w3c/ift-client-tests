import sys
import struct
import pprint
from pathlib import Path
from typing import List, Dict, Union

sys.path.append(str(Path(__file__).resolve().parent.parent))
from testCaseGeneratorLib.iftFile import IFTFile


iftFile = IFTFile("exampleTestFile", "GLYF", "myfont-mod.ift.woff2")
iftData = iftFile.getIFTTableData()

adjustments = [52,35,20,0] # TODO: this should not be necessary. This means I'm missing data
tag_size = 4
def read_uint24(binary_data, offset):
    """Reads a uint24 value from binary data starting at a given offset."""
    bytes_24 = binary_data[offset:offset + 3]
    uint24_value = int.from_bytes(bytes_24, byteorder='big')
    return uint24_value

def read_uint24_array(data, offset, count):
    """Read an array of uint24 values from binary data.
    
    Args:
        data (bytes): The binary data.
        offset (int): The offset to start reading from.
        count (int): The number of uint24 values to read.
        
    Returns:
        list of int: A list of uint24 values.
    """
    uint24_array = []
    for _ in range(count):
        uint24_value = read_uint24(data, offset)
        uint24_array.append(uint24_value)
        offset += 3  # Move to the next 24-bit integer
        
    return uint24_array

def is_bit_set(  number,  bit_position):
     new_num = number >> (bit_position)
     return (new_num & 1)


def get_design_spaces(table_data, design_space_count, current_offset):
    design_spaces = []
    for _ in range(design_space_count):
        design_space = {}
        tags, current_offset = get_tags(table_data, 1, current_offset)
        design_space["tag"] = tags[0]
        design_space["start"] = struct.unpack('I', table_data[current_offset:current_offset+4])[0]
        current_offset += 4
        design_space["end"] = struct.unpack('I', table_data[current_offset:current_offset+4])[0]
        current_offset += 4
        design_spaces.append(design_space)
    return design_spaces, current_offset

def get_tags(table_data, tag_count, current_offset):
    features = []
    for _ in range(tag_count):
        # Extract the 4-byte tag
        tag_bytes = table_data[current_offset:current_offset + tag_size]
        # Convert bytes to a string (assuming it's in ASCII)
        tag = tag_bytes.decode('ascii')
        features.append(tag)
        # Move to the next tag
        current_offset += tag_size
    return features, current_offset

def get_entries(table_data, entry_count, current_offset):
    """Reads the entries from the font data."""
    entries = []
    # for _ in range(entry_count): #TODO: put this back after feature reading is implemented
    for i in range(4):
        entry = {}
        # uint8	formatFlags
        entry['format_flags'] = struct.unpack('B', table_data[current_offset:current_offset+1])[0]
        current_offset += 1
        print(entry['format_flags'])    
        bit0 = is_bit_set(entry['format_flags'],0)
        bit1 = is_bit_set(entry['format_flags'],1)
        bit2 = is_bit_set(entry['format_flags'],2)
        bit3 = is_bit_set(entry['format_flags'],3)
        bit4 = is_bit_set(entry['format_flags'],4)
        bit5 = is_bit_set(entry['format_flags'],5)
        # uint8	featureCount
        if (bit0 == 1):
            print("bit0 set")
            entry['feature_count'] = struct.unpack('B', table_data[current_offset:current_offset+1])[0]  
            current_offset += 1
            print("feature count",entry['feature_count'])
            # Tag	featureTags[featureCount] 
            entry['feature_tags'], current_offset = get_tags(table_data, entry['feature_count'], current_offset)
            # uint16	designSpaceCount
            entry['design_space_count'] = struct.unpack('>H', table_data[current_offset:current_offset+2])[0]
            current_offset += 2
            # Design Space Segment	designSpaceSegments[designSpaceCount]
            entry['design_space_segments'],current_offset = get_design_spaces(table_data, entry['design_space_count'], current_offset)
        if (bit1 == 1):
            print("bit1 set")
            # uint8	copyCount
            entry['copyCount'] = struct.unpack('>H', table_data[current_offset:current_offset+2])[0]
            current_offset += 2
            # uint24	copyIndices[copyCount]
            entry['copyIndices'] = read_uint24_array(table_data, current_offset, entry['copyCount'])
            current_offset += entry['copyCount'] * 3
        if (bit2 == 1):
            print("bit2 set")
            # int24	entryIdDelta
            entry['entry_id_delta'] = read_uint24(table_data, current_offset)
            current_offset += 3
            # uint16	entryIdStringLength
            entry['entry_id_string_length'] = struct.unpack('>H', table_data[current_offset:current_offset+2])[0]
            current_offset += 2
        if (bit3 == 1):
            print("bit3 set")
            # uint8	patchEncoding
            entry['patch_encoding'] = struct.unpack('B', table_data[current_offset:current_offset+1])[0]
            current_offset += 1
        # uint16/uint24	bias
        if  bit4 == 0 and bit5 == 1:
            print("bit4 not set, bit5 set")
            # Read uint16 bias value
            entry['bias_value'] = struct.unpack_from('>H', table_data, current_offset)[0]
            current_offset += 2
        elif bit4 == 1 and bit5 == 1:
            print("bit4 set, bit5 set")
            # Read uint24 bias value
            entry['bias_value'] = int.from_bytes(table_data[current_offset:current_offset + 3], byteorder='big')
            current_offset += 3
        if bit4 == 1 or bit5 == 1:
            print("bit4 set or bit5 set")
            # uint8	codepoints[variable]
            print("crazy stuff") 
        current_offset+= adjustments[i] # TODO: why is this happening? 

        entries.append(entry)
    return entries, current_offset

def parse_ift(iftData):
    # Get the table data
    patch_map_table_data = {}
    current_offset = 0; 


    # uint8	format
    new_offset = current_offset + 1
    patch_map_table_data['format'] = struct.unpack('B', iftData[current_offset:new_offset])[0]

    # uint32	reserved
    current_offset = new_offset
    new_offset = current_offset + 4
    patch_map_table_data['reserved'] = struct.unpack('I', iftData[current_offset:new_offset])[0]


    # uint32	compatibilityId[4]
    current_offset = new_offset
    format_string = '>4I'
    new_offset = current_offset + struct.calcsize(format_string);
    data_segment = iftData[current_offset:new_offset]
    patch_map_table_data['compatibility_id'] = struct.unpack(format_string, data_segment)

    # uint8	defaultPatchEncoding
    current_offset = new_offset
    new_offset = current_offset + 1
    patch_map_table_data['default_patch_encoding'] = struct.unpack('B', iftData[current_offset:new_offset])[0]

    # uint24	entryCount (uint16)
    current_offset = new_offset
    new_offset = current_offset + 2
    patch_map_table_data['entry_count'] = struct.unpack('>H', iftData[current_offset:new_offset])[0]

    # Offset32	entries
    current_offset = new_offset
    new_offset = current_offset + 4
    patch_map_table_data['entries_location'] = struct.unpack('>I', iftData[current_offset:new_offset])[0]

    # Offset32	entryIdStringData
    current_offset = new_offset
    new_offset = current_offset + 4
    patch_map_table_data['entry_id_string_data'] = struct.unpack('>I', iftData[current_offset:new_offset])[0]

    # uint16	uriTemplateLength
    current_offset = new_offset 
    new_offset = current_offset + 2
    patch_map_table_data['uri_template_length'] = struct.unpack('>H', iftData[current_offset:new_offset])[0]


    pprint.pp(patch_map_table_data)
    # uint8	uriTemplate[uri_template_length]
#    current_offset = new_offset
#    new_offset = current_offset + patch_map_table_data['uri_template_length']
#    patch_map_table_data['uri_template'] = iftData[current_offset:new_offset].decode('ascii')
#    patch_map_table_data['entries'],current_offset = get_entries(iftData, patch_map_table_data['entry_count'], patch_map_table_data['entries_location'])
#    print(current_offset)



# List the tables in the WOFF2 file
parse_ift(iftData)
