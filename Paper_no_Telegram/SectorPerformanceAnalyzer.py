#!/usr/bin/env python3
"""
Sector Performance Analyzer
Based on NseUtility.ipynb cells 1-5 content
Provides sector analysis and returns best performing sector stocks for trading
Now includes lot size filtering from CSV
"""

from NseUtility import NseUtils
import time
from datetime import datetime
import pandas as pd
import nsepython
import pprint
import os

class SectorPerformanceAnalyzer:
    def __init__(self, lot_size_csv_path="Dhan - Nse Fno Lot Size.csv"):
        self.nse = NseUtils()
        self.lot_size_csv_path = lot_size_csv_path
        self.lot_size_df = None
        self.load_lot_size_data()
        
        self.sectoral_indices = [
            "NIFTY INDIA CONSUMPTION",
            "NIFTY FINANCIAL SERVICES",
            "NIFTY PHARMA",
            "NIFTY AUTO",
            "NIFTY PRIVATE BANK",
            "NIFTY COMMODITIES",
            "NIFTY MNC",
            "NIFTY BANK",
            "NIFTY METAL",
            "NIFTY SERVICES SECTOR",
            "NIFTY PSE",
            "NIFTY INFRASTRUCTURE",
            #"NIFTY SMALLCAP 100",
            "NIFTY MIDCAP 50",
            "NIFTY PSU BANK",
            "NIFTY ENERGY",
            "NIFTY IT",
            "NIFTY FMCG",
            "NIFTY CPSE",
            "NIFTY OIL & GAS",
            #"NIFTY NEXT 50",
            "NIFTY 50",
            "NIFTY GROWTH SECTORS 15",
            #"NIFTY 100",
            #"NIFTY 500",
            "NIFTY MIDCAP 100",
            #"NIFTY FINANCIAL SERVICES 25/50",
            "NIFTY REALTY",
            "NIFTY HEALTHCARE INDEX",
            "NIFTY CONSUMER DURABLES"
        ]

    def load_lot_size_data(self):
        """
        Load lot size data from CSV file
        """
        try:
            if not os.path.exists(self.lot_size_csv_path):
                print(f"⚠️ Warning: Lot size CSV file not found at {self.lot_size_csv_path}")
                print("   Lot size filtering will be skipped.")
                return
            
            # Read CSV file
            self.lot_size_df = pd.read_csv(self.lot_size_csv_path)
            
            # Clean column names
            self.lot_size_df.columns = self.lot_size_df.columns.str.strip()
            
            print(f"✅ Loaded lot size data: {len(self.lot_size_df)} stocks")
            print(f"   Columns: {list(self.lot_size_df.columns)}")
            
        except Exception as e:
            print(f"⚠️ Error loading lot size CSV: {e}")
            print("   Lot size filtering will be skipped.")
            self.lot_size_df = None

    def filter_by_lot_size(self, stock_symbols):
        """
        Filter stocks based on lot size criteria:
        1. Lot sizes must be equal across all months (Oct, Nov, Dec 2025)
        2. Lot size must be <= 1000
        3. Exclude lot sizes of 15 and 25
        
        Returns filtered list of stock symbols
        """
        if self.lot_size_df is None or len(stock_symbols) == 0:
            print("⚠️ Lot size filtering skipped (no CSV data or no stocks)")
            return stock_symbols
        
        print(f"\n{'='*80}")
        print("APPLYING LOT SIZE FILTERS")
        print(f"{'='*80}")
        print(f"Input stocks: {len(stock_symbols)}")
        
        filtered_stocks = []
        excluded_stocks = {
            'not_in_csv': [],
            'unequal_lots': [],
            'exceeds_1000': [],
            'lot_15_or_25': []
        }
        
        # Identify lot size columns (looking for patterns like "Lot Size (Oct 2025)")
        lot_size_cols = [col for col in self.lot_size_df.columns if 'Lot Size' in col]
        
        if len(lot_size_cols) == 0:
            print("⚠️ No lot size columns found in CSV")
            return stock_symbols
        
        print(f"Found lot size columns: {lot_size_cols}")
        
        for symbol in stock_symbols:
            # Find stock in CSV (case-insensitive match)
            stock_row = self.lot_size_df[self.lot_size_df['Symbol'].str.upper() == symbol.upper()]
            
            if stock_row.empty:
                excluded_stocks['not_in_csv'].append(symbol)
                continue
            
            # Extract lot sizes for all months
            lot_sizes = []
            for col in lot_size_cols:
                try:
                    lot_size = int(stock_row.iloc[0][col])
                    lot_sizes.append(lot_size)
                except (ValueError, KeyError, IndexError):
                    excluded_stocks['not_in_csv'].append(symbol)
                    break
            
            if len(lot_sizes) != len(lot_size_cols):
                continue
            
            # Check if all lot sizes are equal
            if len(set(lot_sizes)) != 1:
                excluded_stocks['unequal_lots'].append(f"{symbol} (lots: {lot_sizes})")
                continue
            
            lot_size = lot_sizes[0]
            
            # Check if lot size exceeds 1000
            if lot_size > 1000:
                excluded_stocks['exceeds_1000'].append(f"{symbol} (lot: {lot_size})")
                continue
            
            # Check if lot size is 15 or 25
            if lot_size in [15, 25]:
                excluded_stocks['lot_15_or_25'].append(f"{symbol} (lot: {lot_size})")
                continue
            
            # Stock passed all filters
            filtered_stocks.append(symbol)
        
        # Print filtering summary
        print(f"\n{'─'*80}")
        print("FILTERING RESULTS:")
        print(f"{'─'*80}")
        print(f"✅ Passed all filters: {len(filtered_stocks)} stocks")
        
        if excluded_stocks['not_in_csv']:
            print(f"\n❌ Not found in CSV: {len(excluded_stocks['not_in_csv'])} stocks")
            print(f"   {', '.join(excluded_stocks['not_in_csv'][:10])}" + 
                  (f"... and {len(excluded_stocks['not_in_csv'])-10} more" if len(excluded_stocks['not_in_csv']) > 10 else ""))
        
        if excluded_stocks['unequal_lots']:
            print(f"\n❌ Unequal lot sizes across months: {len(excluded_stocks['unequal_lots'])} stocks")
            print(f"   {', '.join(excluded_stocks['unequal_lots'][:5])}" + 
                  (f"... and {len(excluded_stocks['unequal_lots'])-5} more" if len(excluded_stocks['unequal_lots']) > 5 else ""))
        
        if excluded_stocks['exceeds_1000']:
            print(f"\n❌ Lot size > 1000: {len(excluded_stocks['exceeds_1000'])} stocks")
            print(f"   {', '.join(excluded_stocks['exceeds_1000'][:5])}" +
                  (f"... and {len(excluded_stocks['exceeds_1000'])-5} more" if len(excluded_stocks['exceeds_1000']) > 5 else ""))
        
        if excluded_stocks['lot_15_or_25']:
            print(f"\n❌ Lot size is 15 or 25: {len(excluded_stocks['lot_15_or_25'])} stocks")
            print(f"   {', '.join(excluded_stocks['lot_15_or_25'][:10])}")
        
        print(f"\n{'='*80}")
        print(f"FINAL FILTERED WATCHLIST: {len(filtered_stocks)} stocks")
        print(f"{'='*80}")
        
        if filtered_stocks:
            print(f"Stocks: {', '.join(filtered_stocks[:30])}" + 
                  (f"... and {len(filtered_stocks)-30} more" if len(filtered_stocks) > 30 else ""))
        
        return filtered_stocks

    def safe_float_convert(self, value, default=0.0):
        """Safely convert value to float"""
        if value is None or value == "" or value == "-" or pd.isna(value):
            return default
        try:
            return float(str(value).replace(",", ""))
        except (ValueError, AttributeError, TypeError):
            return default

    def fetch_index_data(self, index_name):
        """
        Fetch index data using NseUtility
        Returns: DataFrame from get_index_details()
        """
        try:
            df = self.nse.get_index_details(index_name)

            if df is None:
                return None

            if isinstance(df, pd.DataFrame):
                if df.empty:
                    return None
                return df

            elif isinstance(df, dict):
                return pd.DataFrame([df])

            return None

        except Exception as e:
            return None

    def extract_index_info(self, df_result, index_name):
        """
        Extract relevant information from DataFrame result
        Handles various column name formats
        """
        try:
            if df_result is None or df_result.empty:
                return None

            if len(df_result) > 0:
                row = df_result.iloc[0]
            else:
                return None

            def get_value(row, *keys):
                for key in keys:
                    if key in row.index:
                        val = row[key]
                        if pd.notna(val):
                            return val
                return None

            ltp = self.safe_float_convert(get_value(row, 'last', 'lastPrice', 'ltp', 'Last', 'close', 'Close'))
            prev_close = self.safe_float_convert(get_value(row, 'previousClose', 'prevClose', 'PreviousClose', 'Prev Close'))
            open_price = self.safe_float_convert(get_value(row, 'open', 'Open', 'openPrice'))
            high_price = self.safe_float_convert(get_value(row, 'dayHigh', 'high', 'High', 'highPrice'))
            low_price = self.safe_float_convert(get_value(row, 'dayLow', 'low', 'Low', 'lowPrice'))
            change = self.safe_float_convert(get_value(row, 'change', 'Change', 'priceChange'))
            change_pct = self.safe_float_convert(get_value(row, 'pChange', 'percChange', 'percentChange', 'Change%', 'pctChange'))

            if change == 0.0 and ltp > 0 and prev_close > 0:
                change = ltp - prev_close

            if change_pct == 0.0 and change != 0.0 and prev_close > 0:
                change_pct = (change / prev_close) * 100

            timestamp = get_value(row, 'timestamp', 'lastUpdateTime', 'timeVal', 'Time', 'LastUpdate') or "N/A"
            sector_name = get_value(row, 'name', 'indexName', 'symbol', 'Symbol', 'Index') or index_name

            return {
                "Sector": sector_name,
                "LTP": ltp,
                "Open": open_price,
                "High": high_price,
                "Low": low_price,
                "Prev Close": prev_close,
                "Change": change,
                "Change %": change_pct,
                "Updated": timestamp
            }

        except Exception as e:
            return None

    def smart_extract_stocks_from_df(self, df, index_name):
        """
        Intelligently extract stocks from DataFrame returned by get_index_details()
        Handles multiple possible DataFrame structures
        Returns: (index_info, stocks_list)
        """
        try:
            if df is None or df.empty:
                return None, None

            index_info = None
            stocks = []

            SYMBOL_COLS = ['symbol', 'Symbol', 'SYMBOL', 'stock', 'Stock', 'ticker', 'Ticker']
            NAME_COLS = ['name', 'Name', 'companyName', 'Company', 'company', 'stockName']
            LTP_COLS = ['last', 'lastPrice', 'ltp', 'LTP', 'close', 'Close', 'price', 'Price']
            CHANGE_PCT_COLS = ['pChange', 'percChange', 'percentChange', 'Change%', 'change%', 'pctChange', 'changePercent']

            def find_column(df, possible_names):
                for name in possible_names:
                    if name in df.columns:
                        return name
                return None

            symbol_col = find_column(df, SYMBOL_COLS)
            name_col = find_column(df, NAME_COLS)
            ltp_col = find_column(df, LTP_COLS)
            change_col = find_column(df, CHANGE_PCT_COLS)

            if symbol_col:
                first_symbol = df.iloc[0][symbol_col] if len(df) > 0 else None

                start_idx = 0
                if pd.isna(first_symbol) or first_symbol == "" or first_symbol == index_name:
                    start_idx = 1

                    if len(df) > 0 and ltp_col and change_col:
                        index_ltp = self.safe_float_convert(df.iloc[0][ltp_col])
                        index_change = self.safe_float_convert(df.iloc[0][change_col])

                        if index_ltp > 0 or index_change != 0:
                            index_info = {
                                "Sector": index_name,
                                "LTP": index_ltp,
                                "Change %": index_change
                            }

                for idx in range(start_idx, len(df)):
                    row = df.iloc[idx]

                    symbol = row[symbol_col] if symbol_col else None
                    if pd.isna(symbol) or symbol == "" or symbol == index_name:
                        continue

                    company = row[name_col] if name_col else symbol
                    stock_ltp = self.safe_float_convert(row[ltp_col]) if ltp_col else 0.0
                    stock_change = self.safe_float_convert(row[change_col]) if change_col else 0.0

                    if symbol and (stock_ltp > 0 or stock_change != 0):
                        stocks.append({
                            'Symbol': str(symbol).strip(),
                            'Company': str(company).strip() if company else str(symbol).strip(),
                            'LTP': stock_ltp,
                            'Change %': stock_change
                        })

            else:
                if len(df) > 0 and ltp_col and change_col:
                    index_ltp = self.safe_float_convert(df.iloc[0][ltp_col])
                    index_change = self.safe_float_convert(df.iloc[0][change_col])

                    index_info = {
                        "Sector": index_name,
                        "LTP": index_ltp,
                        "Change %": index_change
                    }

            if not index_info and len(df) > 0:
                if ltp_col and change_col:
                    index_info = {
                        "Sector": index_name,
                        "LTP": self.safe_float_convert(df.iloc[0][ltp_col]),
                        "Change %": self.safe_float_convert(df.iloc[0][change_col])
                    }

            return index_info, stocks if stocks else None

        except Exception as e:
            return None, None

    def get_sector_performance(self):
        """
        Get sector performance analysis
        Returns DataFrame of sectors sorted by performance
        """
        sector_data = []

        print("Fetching sectoral indices data...")

        for idx, sector in enumerate(self.sectoral_indices, 1):
            print(f"[{idx:2d}/{len(self.sectoral_indices)}] {sector:<35}", end=" ")

            try:
                df_result = self.fetch_index_data(sector)

                if df_result is None:
                    print("❌ No data")
                    continue

                index_info = self.extract_index_info(df_result, sector)

                if index_info is None:
                    print("❌ Extraction failed")
                    continue

                if index_info["LTP"] == 0 and index_info["Prev Close"] == 0:
                    print("❌ Invalid data")
                    continue

                sector_data.append(index_info)
                print(f"✅ {index_info['Change %']:>6.2f}%")

            except Exception as e:
                print(f"❌ Error: {str(e)}")
                continue

            time.sleep(0.3)

        if not sector_data:
            print("\n⚠️ No data fetched. Check your internet connection or try again later.")
            return None

        df = pd.DataFrame(sector_data).sort_values("Change %", ascending=False)
        return df

    def fetch_all_sector_data(self):
        """
        Fetch all sector data once and return for reuse
        Returns (all_indices_data, all_stocks_by_index)
        """
        all_indices_data = []
        all_stocks_by_index = {}

        print("Fetching sectoral data with constituent stocks...")

        for idx, sector in enumerate(self.sectoral_indices, 1):
            print(f"[{idx:2d}/{len(self.sectoral_indices)}] {sector:<35}", end=" ")

            try:
                df = self.nse.get_index_details(sector)

                if df is None or df.empty:
                    print("❌ No data")
                    continue

                index_info, stocks = self.smart_extract_stocks_from_df(df, sector)

                if index_info is None:
                    print("❌ Extraction failed")
                    continue

                all_indices_data.append(index_info)

                if stocks and len(stocks) > 0:
                    all_stocks_by_index[sector] = stocks
                    print(f"✅ {index_info['Change %']:>6.2f}% | {len(stocks)} stocks")
                else:
                    print(f"✅ {index_info['Change %']:>6.2f}% | No stocks")

            except Exception as e:
                print(f"❌ Error: {str(e)}")
                continue

            time.sleep(0.3)

        return all_indices_data, all_stocks_by_index

    def get_best_performing_sector_stocks(self, all_indices_data, all_stocks_by_index, top_sectors=5):
	    """
		Get stocks from best performing sectors using pre-fetched data
		For each sector, selects top 5 gainers AND top 5 losers
		Returns list of stock symbols for trading
		"""
	    if not all_indices_data:
		    return None

	    df_indices = pd.DataFrame(all_indices_data).sort_values("Change %", ascending=False)
	    top_gainers = df_indices.head(top_sectors)

	    best_stocks = []

	    print(f"\nSelecting stocks from top {top_sectors} performing sectors:")

	    for _, row in top_gainers.iterrows():
		    sector_name = row['Sector']
		    print(f"  📈 {sector_name} ({row['Change %']:+.2f}%)")

		    if sector_name in all_stocks_by_index:
			    stocks = all_stocks_by_index[sector_name]
			    stocks_df = pd.DataFrame(stocks).sort_values('Change %', ascending=False)

			    # Get top 5 gainers from this sector
			    top_5_gainers = stocks_df.head(5)['Symbol'].tolist()

			    # Get top 5 losers from this sector
			    top_5_losers = stocks_df.tail(5)['Symbol'].tolist()
			    top_5_losers.reverse()  # Reverse to show worst first

			    # Combine gainers and losers
			    sector_stocks = top_5_gainers + top_5_losers
			    best_stocks.extend(sector_stocks)

			    print(f"      Added {len(sector_stocks)} stocks:")
			    print(f"        Gainers: {', '.join(top_5_gainers)}")
			    print(f"        Losers:  {', '.join(top_5_losers)}")
		    else:
			    print(f"      ⚠️ No constituent stocks available")

	    # Remove duplicates while preserving order
	    unique_stocks = []
	    seen = set()
	    for stock in best_stocks:
		    if stock not in seen:
			    unique_stocks.append(stock)
			    seen.add(stock)

	    print(f"\nTotal unique stocks selected: {len(unique_stocks)}")
	    return unique_stocks

    def get_worst_performing_sector_stocks(self, all_indices_data, all_stocks_by_index, top_sectors=5):
	    """
		Get stocks from worst performing sectors using pre-fetched data
		For each sector, selects top 5 gainers AND top 5 losers
		Returns list of stock symbols for trading
		"""
	    if not all_indices_data:
		    return None

	    df_indices = pd.DataFrame(all_indices_data).sort_values("Change %", ascending=True)
	    top_losers = df_indices.head(top_sectors)

	    worst_stocks = []

	    print(f"\nSelecting stocks from top {top_sectors} worst performing sectors:")

	    for _, row in top_losers.iterrows():
		    sector_name = row['Sector']
		    print(f"  📉 {sector_name} ({row['Change %']:+.2f}%)")

		    if sector_name in all_stocks_by_index:
			    stocks = all_stocks_by_index[sector_name]
			    stocks_df = pd.DataFrame(stocks).sort_values('Change %', ascending=False)

			    # Get top 5 gainers from this sector
			    top_5_gainers = stocks_df.head(5)['Symbol'].tolist()

			    # Get top 5 losers from this sector
			    top_5_losers = stocks_df.tail(5)['Symbol'].tolist()
			    top_5_losers.reverse()  # Reverse to show worst first

			    # Combine gainers and losers
			    sector_stocks = top_5_gainers + top_5_losers
			    worst_stocks.extend(sector_stocks)

			    print(f"      Added {len(sector_stocks)} stocks:")
			    print(f"        Gainers: {', '.join(top_5_gainers)}")
			    print(f"        Losers:  {', '.join(top_5_losers)}")
		    else:
			    print(f"      ⚠️ No constituent stocks available")

	    # Remove duplicates while preserving order
	    unique_stocks = []
	    seen = set()
	    for stock in worst_stocks:
		    if stock not in seen:
			    unique_stocks.append(stock)
			    seen.add(stock)

	    print(f"\nTotal unique stocks selected from worst sectors: {len(unique_stocks)}")
	    return unique_stocks

    def get_fno_stocks_from_best_sectors(self, all_indices_data, all_stocks_by_index, top_sectors=5, apply_lot_filter=True):
        """
        Get F&O stocks from best performing sectors using pre-fetched data
        Optionally applies lot size filtering
        Returns list of F&O stock symbols for trading
        """
        try:
            # Get F&O stock list
            fno_stocks = set(nsepython.fnolist())
            
            # Get best sector stocks
            sector_stocks = self.get_best_performing_sector_stocks(all_indices_data, all_stocks_by_index, top_sectors)
            
            if not sector_stocks:
                return None
            
            # Filter for F&O stocks only
            fno_sector_stocks = [stock for stock in sector_stocks if stock in fno_stocks]
            
            print(f"\nFiltered to F&O stocks: {len(fno_sector_stocks)} out of {len(sector_stocks)}")
            
            # Apply lot size filtering if enabled
            if apply_lot_filter:
                fno_sector_stocks = self.filter_by_lot_size(fno_sector_stocks)
            else:
                print(f"F&O stocks from best sectors: {', '.join(fno_sector_stocks[:20])}")
            
            return fno_sector_stocks
            
        except Exception as e:
            print(f"Error getting F&O stocks: {e}")
            return None

    def get_fno_stocks_from_worst_sectors(self, all_indices_data, all_stocks_by_index, top_sectors=5, apply_lot_filter=True):
        """
        Get F&O stocks from worst performing sectors using pre-fetched data
        Optionally applies lot size filtering
        Returns list of F&O stock symbols for trading
        """
        try:
            # Get F&O stock list
            fno_stocks = set(nsepython.fnolist())
            
            # Get worst sector stocks
            sector_stocks = self.get_worst_performing_sector_stocks(all_indices_data, all_stocks_by_index, top_sectors)
            
            if not sector_stocks:
                return None
            
            # Filter for F&O stocks only
            fno_sector_stocks = [stock for stock in sector_stocks if stock in fno_stocks]
            
            print(f"\nFiltered to F&O stocks: {len(fno_sector_stocks)} out of {len(sector_stocks)}")
            
            # Apply lot size filtering if enabled
            if apply_lot_filter:
                fno_sector_stocks = self.filter_by_lot_size(fno_sector_stocks)
            else:
                print(f"F&O stocks from worst sectors: {', '.join(fno_sector_stocks[:20])}")
            
            return fno_sector_stocks
            
        except Exception as e:
            print(f"Error getting F&O stocks from worst sectors: {e}")
            return None

    def get_combined_fno_stocks(self, top_gainer_sectors=5, top_loser_sectors=5, apply_lot_filter=True):
        """
        Get combined F&O stocks from both best and worst performing sectors
        Fetches sector data only once for efficiency
        Optionally applies lot size filtering (enabled by default)
        Returns list of F&O stock symbols for trading
        """
        try:
            # Fetch all sector data once
            print("Fetching sector data once for both gainers and losers...")
            all_indices_data, all_stocks_by_index = self.fetch_all_sector_data()
            
            if not all_indices_data:
                print("❌ No sector data available")
                return None
            
            print("\n" + "="*80)
            print("Getting F&O stocks from best performing sectors...")
            print("="*80)
            best_stocks = self.get_fno_stocks_from_best_sectors(
                all_indices_data, 
                all_stocks_by_index, 
                top_gainer_sectors,
                apply_lot_filter=False  # Apply filter at the end
            )
            
            print("\n" + "="*80)
            print("Getting F&O stocks from worst performing sectors...")
            print("="*80)
            worst_stocks = self.get_fno_stocks_from_worst_sectors(
                all_indices_data, 
                all_stocks_by_index, 
                top_loser_sectors,
                apply_lot_filter=False  # Apply filter at the end
            )
            
            combined_stocks = []
            
            if best_stocks:
                combined_stocks.extend(best_stocks)
                print(f"\n✅ Added {len(best_stocks)} F&O stocks from top gainer sectors")
            
            if worst_stocks:
                combined_stocks.extend(worst_stocks)
                print(f"✅ Added {len(worst_stocks)} F&O stocks from top loser sectors")
            
            # Remove duplicates while preserving order
            unique_combined = []
            seen = set()
            for stock in combined_stocks:
                if stock not in seen:
                    unique_combined.append(stock)
                    seen.add(stock)
            
            print(f"\n🎯 Total unique F&O stocks before lot filter: {len(unique_combined)}")
            
            # Apply lot size filtering to combined list
            if apply_lot_filter:
                unique_combined = self.filter_by_lot_size(unique_combined)
            else:
                print(f"Combined watchlist: {', '.join(unique_combined[:30])}")
            
            return unique_combined
            
        except Exception as e:
            print(f"Error getting combined F&O stocks: {e}")
            return None

def get_sector_watchlist(apply_lot_filter=True):
    """
    Main function to get watchlist from best and worst performing sectors
    Returns list of F&O stocks from top 5 gainer and top 5 loser sectors
    With lot size filtering applied by default
    """
    analyzer = SectorPerformanceAnalyzer()
    
    print("="*80)
    print("SECTOR PERFORMANCE ANALYSIS")
    print("="*80)
    
    # Get F&O stocks from both best and worst sectors
    watchlist = analyzer.get_combined_fno_stocks(
        top_gainer_sectors=5, 
        top_loser_sectors=5,
        apply_lot_filter=apply_lot_filter
    )
    
    if watchlist:
        print(f"\n" + "="*80)
        print(f"✅ FINAL WATCHLIST: {len(watchlist)} F&O stocks")
        print(f"   (From top 5 gainer + top 5 loser sectors)")
        if apply_lot_filter:
            print(f"   (With lot size filters applied)")
        print("="*80)
        return watchlist
    else:
        print("\n❌ Failed to generate sector-based watchlist")
        return None

if __name__ == "__main__":
    # Test the sector analyzer
    analyzer = SectorPerformanceAnalyzer()
    
    # Get sector performance
    print("\n" + "="*80)
    print("SECTOR PERFORMANCE OVERVIEW")
    print("="*80)
    sector_df = analyzer.get_sector_performance()
    if sector_df is not None:
        print("\nTop 5 Gainer Sectors:")
        print(sector_df.head()[['Sector', 'Change %']].to_string(index=False))
        print("\nTop 5 Loser Sectors:")
        print(sector_df.tail()[['Sector', 'Change %']].to_string(index=False))
    
    # Get watchlist with lot size filtering
    print("\n" + "="*80)
    print("GENERATING FILTERED WATCHLIST")
    print("="*80)
    watchlist = get_sector_watchlist(apply_lot_filter=True)
    
    if watchlist:
        print(f"\n" + "="*80)
        print(f"GENERATED WATCHLIST ({len(watchlist)} stocks):")
        print("="*80)
        print(watchlist)
