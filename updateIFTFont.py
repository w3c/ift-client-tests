from fontTools.ttLib import TTFont

in_path  = "myfont.ift.ttf"   # or .ttf
out_path = "myfont-mod.ift.otf"

font = TTFont(in_path)

if "IFT " not in font:
    raise ValueError("IFT table not found in font.")

# Unknown/custom tables are stored as raw bytes on .data
tbl = font["IFT "]
raw = bytearray(tbl.data)

# The first byte is the 'format' (uint8). Set it to 3.
raw[0] = 3

# Put the bytes back and save
tbl.data = bytes(raw)
font.save(out_path)

print("Wrote", out_path)

# --- Inspect the saved font ---
font2 = TTFont(out_path)
ift_tbl = font2["IFT "]
format_value = ift_tbl.data[0]  # first byte is 'format'
print("IFT table format field is now:", format_value)
