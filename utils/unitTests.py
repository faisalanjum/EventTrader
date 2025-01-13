import pandas as pd
from utils.market_session import MarketSessionClassifier
from datetime import datetime, date

#### Unit Tests FOR MarketSessionClassifier Functions ####
# This Tests get_session_times_et from MarketSessionClassifier (first loads QC news csv)
def test_get_market_session():
    """Test market session calculations against known values from NewsQC.csv"""
    
    # Load and prepare the data
    df = pd.read_csv('../News/NewsQC.csv', low_memory=False, on_bad_lines='warn', 
                     thousands=',', index_col=0)
    
    # Fix index
    df.index = pd.to_numeric(df.index, errors='coerce').fillna(-1).astype(int)
    
    # Convert time and calculate market sessions
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df['calculated_session'] = df['time'].apply(MarketSessionClassifier().get_market_session)
    
    # Get non-empty rows and calculate mismatches
    valid_mask = df[['market_session', 'calculated_session']].notnull().all(axis=1)
    valid_df = df[valid_mask]
    
    mismatches = valid_df[valid_df['market_session'] != valid_df['calculated_session']]
    
    # Print statistics using original logic but with valid rows only
    total = len(valid_df)
    diff_count = len(mismatches)
    print(f"Total valid rows: {total:,}")
    print(f"Mismatches: {diff_count:,}")
    print(f"Accuracy: {((total - diff_count) / total) * 100:.2f}%\n")
    
    # Print mismatches if any
    if diff_count > 0:
        print("Mismatches:")
        for _, row in mismatches.iterrows():
            print(f"Time: {row['time']}, Expected: {row['market_session']}, Got: {row['calculated_session']}")




# This Tests get_trading_hours from MarketSessionClassifier
def test_get_trading_hours():
    """
    Test get_trading_hours with all edge cases including:
    1. Regular trading days
    2. Weekends
    3. Holidays
    4. Early close days
    5. DST transitions
    6. Invalid inputs
    """
    classifier = MarketSessionClassifier()
    
    def verify_trading_hours(result, expected_times, expected_is_trading):
        """Helper to verify the structure and content of trading hours result"""
        times, is_trading = result
        assert len(times) == 3, f"Expected tuple of 3 elements, got {len(times)}"
        assert isinstance(is_trading, bool), f"Expected boolean for is_trading, got {type(is_trading)}"
        assert is_trading == expected_is_trading, f"Expected is_trading={expected_is_trading}, got {is_trading}"
        assert times == expected_times, f"Times mismatch:\nExpected: {expected_times}\nGot: {times}"

    test_cases = {
        "regular_trading_day": {
            "input": "2024-03-20",  # Wednesday
            "expected_is_trading": True,
            "expected_times": (
                (  # Previous day (Tuesday)
                    pd.Timestamp('2024-03-19 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-19 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-19 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-19 20:00:00-04:00', tz='US/Eastern')
                ),
                (  # Current day (Wednesday)
                    pd.Timestamp('2024-03-20 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-20 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-20 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-20 20:00:00-04:00', tz='US/Eastern')
                ),
                (  # Next day (Thursday)
                    pd.Timestamp('2024-03-21 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-21 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-21 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-21 20:00:00-04:00', tz='US/Eastern')
                )
            )
        },
        
        "weekend": {
            "input": "2024-03-23",  # Saturday
            "expected_is_trading": False,
            "expected_times": (
                (  # Friday
                    pd.Timestamp('2024-03-22 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-22 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-22 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-22 20:00:00-04:00', tz='US/Eastern')
                ),
                'market_closed',  # Saturday
                (  # Monday
                    pd.Timestamp('2024-03-25 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-25 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-25 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-25 20:00:00-04:00', tz='US/Eastern')
                )
            )
        },
        
        "holiday": {
            "input": "2024-01-01",  # New Year's Day
            "expected_is_trading": False,
            "expected_times": (
                (  # Previous trading day (Friday)
                    pd.Timestamp('2023-12-29 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2023-12-29 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2023-12-29 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2023-12-29 20:00:00-05:00', tz='US/Eastern')
                ),
                'market_closed',  # Holiday
                (  # Next trading day (Tuesday)
                    pd.Timestamp('2024-01-02 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-01-02 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-01-02 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-01-02 20:00:00-05:00', tz='US/Eastern')
                )
            )
        },
        
        "early_close": {
            "input": "2024-07-03",  # Independence Day Eve
            "expected_is_trading": True,
            "expected_times": (
                (  # Previous day
                    pd.Timestamp('2024-07-02 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-02 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-02 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-02 20:00:00-04:00', tz='US/Eastern')
                ),
                (  # Early close day
                    pd.Timestamp('2024-07-03 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-03 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-03 13:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-03 13:00:00-04:00', tz='US/Eastern')
                ),
                (  # Next trading day (Friday)
                    pd.Timestamp('2024-07-05 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-05 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-05 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-07-05 20:00:00-04:00', tz='US/Eastern')
                )
            )
        },
        
        "dst_spring_forward": {
            "input": "2024-03-11",  # Monday after DST starts
            "expected_is_trading": True,
            "expected_times": (
                (  # Friday before DST
                    pd.Timestamp('2024-03-08 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-08 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-08 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-08 20:00:00-05:00', tz='US/Eastern')
                ),
                (  # DST transition day
                    pd.Timestamp('2024-03-11 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-11 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-11 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-11 20:00:00-04:00', tz='US/Eastern')
                ),
                (  # Day after DST
                    pd.Timestamp('2024-03-12 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-12 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-12 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-03-12 20:00:00-04:00', tz='US/Eastern')
                )
            )
        },

        "dst_fall_back": {
            "input": "2024-11-04",  # Monday after DST ends
            "expected_is_trading": True,
            "expected_times": (
                (  # Friday before DST
                    pd.Timestamp('2024-11-01 04:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-01 09:30:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-01 16:00:00-04:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-01 20:00:00-04:00', tz='US/Eastern')
                ),
                (  # DST transition day
                    pd.Timestamp('2024-11-04 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-04 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-04 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-04 20:00:00-05:00', tz='US/Eastern')
                ),
                (  # Day after DST
                    pd.Timestamp('2024-11-05 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-05 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-05 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-11-05 20:00:00-05:00', tz='US/Eastern')
                )
            )
        },

        "christmas_eve_early_close": {
            "input": "2024-12-24",
            "expected_is_trading": True,
            "expected_times": (
                (  # Previous day
                    pd.Timestamp('2024-12-23 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-23 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-23 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-23 20:00:00-05:00', tz='US/Eastern')
                ),
                (  # Christmas Eve early close
                    pd.Timestamp('2024-12-24 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-24 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-24 13:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-24 13:00:00-05:00', tz='US/Eastern')
                ),
                (  # Next trading day (Thursday)
                    pd.Timestamp('2024-12-26 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-26 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-26 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-26 20:00:00-05:00', tz='US/Eastern')
                )
            )
        },

        "year_boundary": {
            "input": "2024-12-31",
            "expected_is_trading": True,
            "expected_times": (
                (  # Previous day
                    pd.Timestamp('2024-12-30 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-30 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-30 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-30 20:00:00-05:00', tz='US/Eastern')
                ),
                (  # New Year's Eve
                    pd.Timestamp('2024-12-31 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-31 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-31 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2024-12-31 20:00:00-05:00', tz='US/Eastern')
                ),
                (  # Next trading day (Jan 2)
                    pd.Timestamp('2025-01-02 04:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2025-01-02 09:30:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2025-01-02 16:00:00-05:00', tz='US/Eastern'),
                    pd.Timestamp('2025-01-02 20:00:00-05:00', tz='US/Eastern')
                )
            )
        },


        
        "invalid_inputs": [
            (None, (None, False)),
            ("invalid_date", (None, False)),
            (pd.NaT, (None, False))
        ]
    }
    
    failures = []
    
    # Test regular cases
    for case_name, case_data in test_cases.items():
        if isinstance(case_data, dict):  # Skip invalid_inputs list
            print(f"\nTesting {case_name}...")
            try:
                result = classifier.get_trading_hours(case_data["input"])
                verify_trading_hours(
                    result,
                    case_data["expected_times"],
                    case_data["expected_is_trading"]
                )
                print(f"✅ Passed: {case_name}")
            except AssertionError as e:
                failures.append(f"{case_name}: {str(e)}")
                print(f"❌ Failed: {case_name} - {str(e)}")
    
    # Test invalid inputs
    print("\nTesting invalid inputs...")
    invalid_inputs = [
        (None, (None, False)),
        ("invalid_date", (None, False)),
        (pd.NaT, (None, False)),
        ("", (None, False)),
        ("2024-13-01", (None, False)),  # Invalid month
        ("2024-04-31", (None, False)),  # Invalid day
        ("not a date", (None, False)),
        ("2024/13/01", (None, False))   # Invalid date format
    ]


    for invalid_input, expected_result in invalid_inputs:
        try:
            result = classifier.get_trading_hours(invalid_input)
            assert result == expected_result, \
                f"Expected {expected_result} for input {invalid_input}, got {result}"
            print(f"✅ Passed: Invalid input {invalid_input}")
        except AssertionError as e:
            failures.append(f"Invalid input {invalid_input}: {str(e)}")
            print(f"❌ Failed: Invalid input {invalid_input} - {str(e)}")
    
    # Final report
    if failures:
        print("\n❌ Test failures:")
        for failure in failures:
            print(f"- {failure}")
        raise AssertionError("Some tests failed")
    else:
        print("\n✅ All tests passed!")

# This Tests get_trading_hours from MarketSessionClassifier against QuantConnect sample data

def test_get_trading_hours_qc():
    """Compare our market session outputs with QuantConnect's outputs"""
    
    classifier = MarketSessionClassifier()
    
    # Complete QuantConnect outputs
    quantconnect_outputs = {
        "2023-12-30": (((pd.Timestamp('2023-12-29 04:00:00-0500', tz='US/Eastern'), 
                         pd.Timestamp('2023-12-29 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 20:00:00-0500', tz='US/Eastern')),
                        'market_closed',
                        (pd.Timestamp('2024-01-02 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 20:00:00-0500', tz='US/Eastern'))), False),
                         
        "2023-12-31": (((pd.Timestamp('2023-12-29 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 20:00:00-0500', tz='US/Eastern')),
                        'market_closed',
                        (pd.Timestamp('2024-01-02 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 20:00:00-0500', tz='US/Eastern'))), False),
                         
        "2024-01-01": (((pd.Timestamp('2023-12-29 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 20:00:00-0500', tz='US/Eastern')),
                        'market_closed',
                        (pd.Timestamp('2024-01-02 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 20:00:00-0500', tz='US/Eastern'))), False),
                         
        "2024-01-02": (((pd.Timestamp('2023-12-29 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2023-12-29 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-02 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-03 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 20:00:00-0500', tz='US/Eastern'))), True),
                         
        "2024-01-03": (((pd.Timestamp('2024-01-02 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-02 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-03 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-04 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 20:00:00-0500', tz='US/Eastern'))), True),
                         
        "2024-01-04": (((pd.Timestamp('2024-01-03 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-03 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-04 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-05 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 20:00:00-0500', tz='US/Eastern'))), True),
                         
        "2024-01-05": (((pd.Timestamp('2024-01-04 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-04 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-05 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-08 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 20:00:00-0500', tz='US/Eastern'))), True),
                         
        "2024-01-06": (((pd.Timestamp('2024-01-05 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 20:00:00-0500', tz='US/Eastern')),
                        'market_closed',
                        (pd.Timestamp('2024-01-08 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 20:00:00-0500', tz='US/Eastern'))), False),
                         
        "2024-01-07": (((pd.Timestamp('2024-01-05 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 20:00:00-0500', tz='US/Eastern')),
                        'market_closed',
                        (pd.Timestamp('2024-01-08 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 20:00:00-0500', tz='US/Eastern'))), False),
                         
        "2024-01-08": (((pd.Timestamp('2024-01-05 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-05 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-08 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-09 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 20:00:00-0500', tz='US/Eastern'))), True),
                         
        "2024-01-09": (((pd.Timestamp('2024-01-08 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-08 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-09 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-10 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 20:00:00-0500', tz='US/Eastern'))), True),
                         
        "2024-01-10": (((pd.Timestamp('2024-01-09 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-09 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-10 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-11 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-11 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-11 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-11 20:00:00-0500', tz='US/Eastern'))), True),
                         
        "2024-01-11": (((pd.Timestamp('2024-01-10 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-10 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-11 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-11 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-11 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-11 20:00:00-0500', tz='US/Eastern')),
                        (pd.Timestamp('2024-01-12 04:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-12 09:30:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-12 16:00:00-0500', tz='US/Eastern'),
                         pd.Timestamp('2024-01-12 20:00:00-0500', tz='US/Eastern'))), True)
    }
    
    failures = []
    
    for date in quantconnect_outputs.keys():
        print(f"\nTesting date: {date}")
        try:
            our_result = classifier.get_trading_hours(date)
            qc_result = quantconnect_outputs[date]
            
            assert our_result == qc_result, \
                f"Mismatch for {date}:\nExpected: {qc_result}\nGot: {our_result}"
            
            print(f"✅ Passed: {date}")
        except AssertionError as e:
            failures.append(f"{date}: {str(e)}")
            print(f"❌ Failed: {date} - {str(e)}")
    
    # Final report
    if failures:
        print("\n❌ Test failures:")
        for failure in failures:
            print(f"- {failure}")
        raise AssertionError("Some tests failed")
    else:
        print("\n✅ All tests match QuantConnect outputs!")