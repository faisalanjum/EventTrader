from datetime import datetime, timezone
import re

# Pre-compile the regex for efficiency if this function is called very frequently
_id_re = re.compile(r"^(?P<base>\d+)\.(?P<ts>.+)$")

def canonicalise_news_full_id(raw_full_id: str) -> str:
    """
    Input : '30661575.2023-02-01T04.29.49-05.00' (timestamp uses . for time separators)
    Output: '30661575.2023-02-01T09.29.49+00.00' (timestamp always rendered in UTC, HH.MM.SS also dot-separated)

    Handles cases where input might already be UTC or malformed.
    """
    if not isinstance(raw_full_id, str):
        # Or raise TypeError, depending on desired strictness
        return str(raw_full_id) 

    m = _id_re.match(raw_full_id)
    if not m:
        return raw_full_id  # Malformed or not matching expected pattern (e.g., just a base ID)
    
    base, ts_with_dots = m.group("base"), m.group("ts")

    try:
        # Replace dots with colons in the time part for robust parsing by fromisoformat
        # Handles YYYY-MM-DDTHH.MM.SS.ffffffZ or YYYY-MM-DDTHH.MM.SS.ffffff+HH:MM etc.
        # Need to be careful not to replace dots in microseconds if present.
        # A common pattern is HH.MM.SS or HH.MM.SS.ffffff.
        # The regex for fromisoformat is quite flexible with T and offset, but colons in time are standard.

        # Simple replacement for HH.MM.SS part first
        ts_for_parsing = ts_with_dots
        if 'T' in ts_for_parsing:
            date_part, time_part_full = ts_for_parsing.split('T', 1)
            time_components = time_part_full.split('.')
            if len(time_components) >= 3: # HH, MM, SS are present
                # Check if the third component (seconds) also contains fractional seconds
                if len(time_components[2]) > 2 and any(c.isdigit() for c in time_components[2][2:]):
                    # Has fractional seconds like SSffffff or SS.ffffff where SS are digits
                    # Reconstruct with colons for HH:MM but keep SS.ffffff as is for a moment
                    # Example: 09.29.49.123456+00.00 -> 09:29:SS.ffffff... 
                    # This part is tricky if fromisoformat doesn't like SS.micros. 
                    # Standard ISO is HH:MM:SS.ffffff
                    # Let's assume the example format HH.MM.SS is strict and there are no further dots for microseconds.
                    # So, 2023-02-01T04.29.49-05.00 -> 2023-02-01T04:29:49-05:00
                    # And 2023-02-01T09.29.49+00.00 -> 2023-02-01T09:29:49+00:00
                    
                    # General strategy: replace first two dots in the time part if they exist after T
                    parts_after_T = time_part_full.split('.')
                    if len(parts_after_T) == 3: # HH.MM.SS (no microseconds, but may have offset)
                        time_part_colon = ':'.join(parts_after_T[:3]) 
                        ts_for_parsing = f"{date_part}T{time_part_colon}"
                    elif len(parts_after_T) > 3: # HH.MM.SS.microseconds... (potentially)
                        time_part_colon = ':'.join(parts_after_T[:2]) # HH:MM
                        # SS.microseconds...offset
                        remaining_time_part = '.'.join(parts_after_T[2:])
                        ts_for_parsing = f"{date_part}T{time_part_colon}:{remaining_time_part}"
                    else: # Could be HH.MM or less, or already has colons.
                          # Fallback to simple replace, fromisoformat is somewhat flexible.
                        ts_for_parsing = ts_with_dots.replace('.', ':', 2) # Replace max 2 dots for HH:MM:SS
                else: # Only one or two components after T split by dot, or has no dots after T
                    ts_for_parsing = ts_with_dots.replace('.', ':', 2)
            else: # No 'T', might be just date or malformed. fromisoformat might handle date-only.
                ts_for_parsing = ts_with_dots.replace('.', ':', 2)

        dt = datetime.fromisoformat(ts_for_parsing)
        dt_utc = dt.astimezone(timezone.utc)
        
        # Format to YYYY-MM-DDTHH.MM.SS+HH.MM (dots for time, dot for offset colon)
        ts_utc_iso = dt_utc.isoformat(timespec="seconds")  # Standard ISO: 2023-02-01T09:29:49+00:00
        
        # Replace colons in time part with dots
        # Replace last colon (in offset) with dot for the desired output format
        if 'T' in ts_utc_iso:
            date_part_utc, time_part_utc_full = ts_utc_iso.split('T', 1)
            if '+' in time_part_utc_full: # Has offset
                time_values, offset_values = time_part_utc_full.split('+',1)
                offset_final = '+' + offset_values.replace(':','.')
            elif '-' in time_part_utc_full:
                time_values, offset_values = time_part_utc_full.split('-',1) # Careful with date preceding 'T'
                offset_final = '-' + offset_values.replace(':','.')
            else: # No offset (e.g. Z for Zulu)
                time_values = time_part_utc_full
                offset_final = '+00.00' # Assume Z means +00:00 and format it
                if time_values.endswith('Z'):
                    time_values = time_values[:-1] # Remove Z

            time_values_dotted = time_values.replace(':','.')
            final_ts_suffix = f"{time_values_dotted}{offset_final}"
            return f"{base}.{date_part_utc}T{final_ts_suffix}"
        else: # Should not happen if fromisoformat worked and it's a datetime
            return f"{base}.{ts_utc_iso.replace(':', '.')}" # Fallback replace all colons

    except Exception as e:
        # If any parsing/conversion error, return original to be safe
        # Consider logging the error: print(f"Error canonicalising {raw_full_id}: {e}")
        return raw_full_id 