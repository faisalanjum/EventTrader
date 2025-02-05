class MetadataFields:
    # Top-level structure
    EVENT = 'event'
    RETURNS_SCHEDULE = 'returns_schedule'
    INSTRUMENTS = 'instruments'
    
    # Event fields
    MARKET_SESSION = 'market_session'
    CREATED = 'created'
    
    # Core return types (single source of truth)
    HOURLY = 'hourly'
    SESSION = 'session'
    DAILY = 'daily'
    
    # Return result fields
    HOURLY_RETURN = f'{HOURLY}_return'
    SESSION_RETURN = f'{SESSION}_return'
    DAILY_RETURN = f'{DAILY}_return'
    
    
    # Mapping for schedule to results
    RETURN_TYPE_MAP = {
        HOURLY: HOURLY_RETURN,
        SESSION: SESSION_RETURN,
        DAILY: DAILY_RETURN
    }