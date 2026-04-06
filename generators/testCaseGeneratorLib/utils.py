import struct

from testCaseGeneratorLib.constants import (
    IFT_ENTRIES_OFFSET_END,
    IFT_ENTRIES_OFFSET_START,
    IFT_ENTRY_ID_STRING_OFFSET_END,
    IFT_ENTRY_ID_STRING_OFFSET_START,
    IFT_FORMAT_OFFSET,
    IFT_URL_TEMPLATE_LENGTH_OFFSET,
    IFT_URL_TEMPLATE_START,
)


def replace_format2_url_template(iftData, new_template):
    """Replace the Format 2 patch map URL template and fix patch-map-relative offsets.

    Layout (§5.3.2 Patch Map Table: Format 2, https://www.w3.org/TR/IFT/#patch-map-format-2):
    bytes 0–32: format … entryIdStringData; 33–34: urlTemplateLength; 35+: urlTemplate;
    then optional cffCharStringsOffset / cff2CharStringsOffset (flags), then remaining
    table bytes (e.g. mapping entries at ``entries``).

    Only ``entries`` and ``entryIdStringData`` in the header are adjusted when template
    length changes; they are Offset32 values from the start of this table. Optional
    CFF charstring offsets immediately after ``urlTemplate`` are copied unchanged —
    they are relative to the CFF/CFF2 table, not the patch map.

    Expand URL Template: https://www.w3.org/TR/IFT/#url-templates
    """
    iftData = bytearray(iftData)
    if iftData[IFT_FORMAT_OFFSET] != 2:
        raise ValueError("Expected IFT patch map format 2")
    old_len = int.from_bytes(
        iftData[IFT_URL_TEMPLATE_LENGTH_OFFSET : IFT_URL_TEMPLATE_LENGTH_OFFSET + 2], "big"
    )
    new_len = len(new_template)
    delta = new_len - old_len
    suffix_start = IFT_URL_TEMPLATE_START + old_len

    new_patch_map = bytearray()
    new_patch_map.extend(iftData[:IFT_URL_TEMPLATE_LENGTH_OFFSET])
    new_patch_map.extend(struct.pack(">H", new_len))
    new_patch_map.extend(new_template)
    new_patch_map.extend(iftData[suffix_start:])

    if delta != 0:
        def adjust_patch_map_offset(offset):
            if offset != 0 and offset >= suffix_start:
                return offset + delta
            return offset

        entries_offset = int.from_bytes(
            new_patch_map[IFT_ENTRIES_OFFSET_START:IFT_ENTRIES_OFFSET_END], "big"
        )

        # update the entries offset
        new_patch_map[IFT_ENTRIES_OFFSET_START:IFT_ENTRIES_OFFSET_END] = struct.pack(
            ">I", adjust_patch_map_offset(entries_offset)
        )
        entry_id_offset = int.from_bytes(
            new_patch_map[IFT_ENTRY_ID_STRING_OFFSET_START:IFT_ENTRY_ID_STRING_OFFSET_END],
            "big",
        )
        # update the entry id string offset
        new_patch_map[IFT_ENTRY_ID_STRING_OFFSET_START:IFT_ENTRY_ID_STRING_OFFSET_END] = (
            struct.pack(">I", adjust_patch_map_offset(entry_id_offset))
        )

    return new_patch_map
