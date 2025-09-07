import pandas as pd

def calculate_vwap_daily(high, low, close, volume, timestamps):
    """Calculate VWAP with daily reset"""
    df_temp = pd.DataFrame({
        'timestamp': pd.to_datetime(timestamps),
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })

    # Group by date
    df_temp['date'] = df_temp['timestamp'].dt.date

    # Calculate typical price and volume*price
    typical_price = (df_temp['high'] + df_temp['low'] + df_temp['close']) / 3
    volume_price = typical_price * df_temp['volume']

    # Calculate VWAP for each day
    vwap_values = []
    for date, group_indices in df_temp.groupby('date').groups.items():
        group_volume_price = volume_price.iloc[group_indices]
        group_volume = df_temp['volume'].iloc[group_indices]

        # Cumulative sums within the day
        cumsum_vp = group_volume_price.cumsum()
        cumsum_vol = group_volume.cumsum()

        day_vwap = cumsum_vp / cumsum_vol
        vwap_values.extend(day_vwap.tolist())

    return pd.Series(vwap_values, index=df_temp.index)