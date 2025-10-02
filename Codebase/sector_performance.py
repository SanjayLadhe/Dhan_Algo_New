#!/usr/bin/env python3
"""
Sector Performance Analyzer
Based on NseUtility.ipynb cells 1-5 content
Provides sector analysis and returns best performing sector stocks for trading
"""

from NseUtility import NseUtils
import time
from datetime import datetime
import pandas as pd
import nsepython
import pprint

class SectorPerformanceAnalyzer:
    def __init__(self):
        self.nse = NseUtils()
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
            "NIFTY SMALLCAP 100",
            "NIFTY MIDCAP 50",
            "NIFTY PSU BANK",
            "NIFTY ENERGY",
            "NIFTY IT",
            "NIFTY FMCG",
            "NIFTY CPSE",
            "NIFTY OIL & GAS",
            "NIFTY NEXT 50",
            "NIFTY 50",
            "NIFTY GROWTH SECTORS 15",
            "NIFTY 100",
            "NIFTY 500",
            "NIFTY MIDCAP 100",
            "NIFTY FINANCIAL SERVICES 25/50",
            "NIFTY REALTY",
            "NIFTY HEALTHCARE INDEX",
            "NIFTY CONSUMER DURABLES"
        ]

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

        for idx, sector in enumerate(self.sectoral_indices, 1):  # Scan all sectoral indices
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
                top_stocks = stocks_df.head(5)['Symbol'].tolist()
                
                best_stocks.extend(top_stocks)
                print(f"      Added {len(top_stocks)} stocks: {', '.join(top_stocks)}")
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
        Returns list of stock symbols for trading
        """
        if not all_indices_data:
            return None

        df_indices = pd.DataFrame(all_indices_data).sort_values("Change %", ascending=True)  # Sort ascending for losers
        top_losers = df_indices.head(top_sectors)

        worst_stocks = []
        
        print(f"\nSelecting stocks from top {top_sectors} worst performing sectors:")
        
        for _, row in top_losers.iterrows():
            sector_name = row['Sector']
            print(f"  📉 {sector_name} ({row['Change %']:+.2f}%)")

            if sector_name in all_stocks_by_index:
                stocks = all_stocks_by_index[sector_name]
                stocks_df = pd.DataFrame(stocks).sort_values('Change %', ascending=False)  # Still get best stocks from worst sectors
                top_stocks = stocks_df.head(5)['Symbol'].tolist()
                
                worst_stocks.extend(top_stocks)
                print(f"      Added {len(top_stocks)} stocks: {', '.join(top_stocks)}")
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

    def get_fno_stocks_from_best_sectors(self, all_indices_data, all_stocks_by_index, top_sectors=5):
        """
        Get F&O stocks from best performing sectors using pre-fetched data
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
            print(f"F&O stocks from best sectors: {', '.join(fno_sector_stocks[:20])}")  # Show first 20
            
            return fno_sector_stocks
            
        except Exception as e:
            print(f"Error getting F&O stocks: {e}")
            return None

    def get_fno_stocks_from_worst_sectors(self, all_indices_data, all_stocks_by_index, top_sectors=5):
        """
        Get F&O stocks from worst performing sectors using pre-fetched data
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
            print(f"F&O stocks from worst sectors: {', '.join(fno_sector_stocks[:20])}")  # Show first 20
            
            return fno_sector_stocks
            
        except Exception as e:
            print(f"Error getting F&O stocks from worst sectors: {e}")
            return None

    def get_combined_fno_stocks(self, top_gainer_sectors=5, top_loser_sectors=5):
        """
        Get combined F&O stocks from both best and worst performing sectors
        Fetches sector data only once for efficiency
        Returns list of F&O stock symbols for trading
        """
        try:
            # Fetch all sector data once
            print("Fetching sector data once for both gainers and losers...")
            all_indices_data, all_stocks_by_index = self.fetch_all_sector_data()
            
            if not all_indices_data:
                print("❌ No sector data available")
                return None
            
            print("Getting F&O stocks from best performing sectors...")
            best_stocks = self.get_fno_stocks_from_best_sectors(all_indices_data, all_stocks_by_index, top_gainer_sectors)
            
            print("\nGetting F&O stocks from worst performing sectors...")
            worst_stocks = self.get_fno_stocks_from_worst_sectors(all_indices_data, all_stocks_by_index, top_loser_sectors)
            
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
            
            print(f"\n🎯 Total unique F&O stocks: {len(unique_combined)}")
            print(f"Combined watchlist: {', '.join(unique_combined[:30])}")  # Show first 30
            
            return unique_combined
            
        except Exception as e:
            print(f"Error getting combined F&O stocks: {e}")
            return None

def get_sector_watchlist():
    """
    Main function to get watchlist from best and worst performing sectors
    Returns list of F&O stocks from top 5 gainer and top 5 loser sectors
    """
    analyzer = SectorPerformanceAnalyzer()
    
    print("="*80)
    print("SECTOR PERFORMANCE ANALYSIS")
    print("="*80)
    
    # Get F&O stocks from both best and worst sectors
    watchlist = analyzer.get_combined_fno_stocks(top_gainer_sectors=5, top_loser_sectors=5)
    
    if watchlist:
        print(f"\n✅ Generated watchlist with {len(watchlist)} F&O stocks from top 5 gainer + top 5 loser sectors")
        return watchlist
    else:
        print("\n❌ Failed to generate sector-based watchlist")
        return None

if __name__ == "__main__":
    # Test the sector analyzer
    analyzer = SectorPerformanceAnalyzer()
    
    # Get sector performance
    sector_df = analyzer.get_sector_performance()
    if sector_df is not None:
        print("\nTop 5 Gainer Sectors:")
        print(sector_df.head()[['Sector', 'Change %']].to_string(index=False))
        print("\nTop 5 Loser Sectors:")
        print(sector_df.tail()[['Sector', 'Change %']].to_string(index=False))
    
    # Get watchlist
    watchlist = get_sector_watchlist()
    if watchlist:
        print(f"\nGenerated Watchlist ({len(watchlist)} stocks):")
        print(watchlist)