"""
Moving Average Crossover Trading Bot - Alpaca Paper Trading (No Pandas)
Based on 50-day and 200-day moving average strategy
Simple version without pandas - works on Python 3.14
"""

import json
import os
from bst import BinarySearchTree
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("Warning: Alpaca not installed yet")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not installed yet")


class SimpleTradingBot:
    """Simple trading bot using moving average crossover - no pandas required"""
    
    def __init__(self, ticker: str, api_key: str = None, secret_key: str = None, paper: bool = True):
        """
        Initialize the trading bot
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            api_key: Alpaca API key (loads from .env if None)
            secret_key: Alpaca Secret key (loads from .env if None)
            paper: Use paper trading (True) or live (False)
        """
        self.ticker = ticker.upper()
        self.paper = paper
        self.prices_list = []
        self.price_tree = BinarySearchTree()  
        self.trades = []
        self.initial_capital = 25000
        self.client = None
        
        # Load credentials
        if api_key is None or secret_key is None:
            load_dotenv()
            api_key = os.getenv('APCA_API_KEY_ID')
            secret_key = os.getenv('APCA_API_SECRET_KEY')
        
        # Connect to Alpaca if credentials available
        if api_key and secret_key and ALPACA_AVAILABLE:
            try:
                self.client = TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)
                account = self.client.get_account()
                self.initial_capital = float(account.cash)
                print(f"✅ Connected to Alpaca ({'Paper Trading' if paper else 'LIVE TRADING'})")
                print(f"   Account Equity: ${float(account.equity):.2f}")
                print(f"   Available Cash: ${float(account.cash):.2f}\n")
            except Exception as e:
                print(f"❌ Alpaca connection failed: {e}")
                print("   Continuing in backtest mode...\n")
                self.client = None
        else:
            if not api_key or not secret_key:
                print("⚠️  No API credentials found. Running in backtest mode.")
                print("   Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in .env file for live trading.\n")
            if not ALPACA_AVAILABLE:
                print("⚠️  Alpaca library not installed. Running in backtest mode.\n")
    
    def fetch_price_data(self, days: int = 400):
        """
        Fetch historical price data from Yahoo Finance
        """
        if not YFINANCE_AVAILABLE:
            print("❌ yfinance not installed. Cannot fetch data.")
            return False

        try:
            print(f"📊 Fetching data for {self.ticker}...")

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            data = yf.download(
                self.ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True
            )

            if data is None or data.empty:
                print(f"❌ No data found for {self.ticker}")
                return False

            # Extract Close prices safely
            close = None

            if "Close" in getattr(data, "columns", []):
                close = data["Close"]
            else:
                if hasattr(data.columns, "get_level_values"):
                    col_names = list(data.columns.get_level_values(-1))
                    if "Close" in col_names:
                        close_col = [c for c in data.columns if c[-1] == "Close"][0]
                        close = data[close_col]

            if close is None:
                close = data.iloc[:, -1]  # fallback

            # If still DataFrame → take first column
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]

            close = close.dropna()

            # Force into 1D float list
            vals = close.to_numpy().reshape(-1)
            self.prices_list = [float(x) for x in vals if x == x]
# Build BST from prices
                # Build BST from prices
            self.price_tree = BinarySearchTree()

            for p in self.prices_list:
                self.price_tree.insert(int(p * 100))  # scale to avoid decimals

            print(f"✅ Fetched {len(self.prices_list)} days of data")
            print(
                f"   Date range: {data.index[0].strftime('%Y-%m-%d')} "
                f"to {data.index[-1].strftime('%Y-%m-%d')}"
            )
            print(f"   Current price: ${self.prices_list[-1]:.2f}\n")

            return True

        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return False


    def calculate_moving_averages(self):
        """Calculate 50-day and 200-day moving averages"""
        
        if len(self.prices_list) < 200:
            return None
        
        # Current MAs
        short_ma = sum(self.prices_list[-50:]) / 50
        long_ma = sum(self.prices_list[-200:]) / 200
        
        # Previous day MAs
        prev_short_ma = sum(self.prices_list[-51:-1]) / 50
        prev_long_ma = sum(self.prices_list[-201:-1]) / 200
        
        return {
            'short_ma': short_ma,
            'long_ma': long_ma,
            'prev_short_ma': prev_short_ma,
            'prev_long_ma': prev_long_ma
        }
    
    def generate_signal(self):
        """Generate BUY, SELL, or HOLD signal"""
        
        if len(self.prices_list) < 200:
            return "Not enough data"
        
        mas = self.calculate_moving_averages()
        if not mas:
            return "Not enough data"
        
        short_ma = mas['short_ma']
        long_ma = mas['long_ma']
        prev_short_ma = mas['prev_short_ma']
        prev_long_ma = mas['prev_long_ma']
        
        # Golden Cross: BUY
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            return "BUY"
        
        # Death Cross: SELL
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            return "SELL"
        
        else:
            return "HOLD"
    
    def get_account_info(self):
        """Get account info from Alpaca"""
        if not self.client:
            return None
        
        try:
            account = self.client.get_account()
            return {
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power)
            }
        except Exception as e:
            print(f"❌ Error getting account info: {e}")
            return None
    
    def get_position(self):
        """Get current position for ticker"""
        if not self.client:
            return None
        
        try:
            positions = self.client.get_all_positions()
            for position in positions:
                if position.symbol == self.ticker:
                    return {
                        'qty': int(position.qty),
                        'avg_fill_price': float(position.avg_fill_price),
                        'market_value': float(position.market_value),
                        'unrealized_pl': float(position.unrealized_pl)
                    }
            return None
        except Exception as e:
            print(f"❌ Error getting position: {e}")
            return None
    
    def execute_order(self, side: str, qty: int):
        """Execute order on Alpaca"""
        if not self.client:
            return None
        
        try:
            order_data = MarketOrderRequest(
                symbol=self.ticker,
                qty=qty,
                side=OrderSide.BUY if side.upper() == 'BUY' else OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            return self.client.submit_order(order_data)
        except Exception as e:
            print(f"❌ Order failed: {e}")
            return None
    
    def execute_trade(self, signal: str, current_price: float):
        """Execute trade based on signal"""
        
        if not self.client:
            print(f"⚪ Demo mode - Signal: {signal}")
            return
        
        account_info = self.get_account_info()
        position = self.get_position()
        
        if signal == "BUY":
            if position and int(position['qty']) > 0:
                print(f"⚪ Already holding {position['qty']} shares")
                return
            
            if not account_info:
                return
            
            shares_to_buy = int(account_info['buying_power'] / current_price * 0.95)
            
            if shares_to_buy > 0:
                print(f"🟢 BUY Signal - Ordering {shares_to_buy} shares @ ${current_price:.2f}")
                order = self.execute_order('buy', shares_to_buy)
                
                if order:
                    self.trades.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'action': 'BUY',
                        'shares': shares_to_buy,
                        'price': current_price,
                        'status': str(order.status)
                    })
                    print(f"   Order ID: {order.id}\n")
            else:
                print(f"⚠️  Insufficient buying power")
        
        elif signal == "SELL":
            if not position or int(position['qty']) == 0:
                print(f"⚪ No shares to sell")
                return
            
            shares_to_sell = int(position['qty'])
            print(f"🔴 SELL Signal - Ordering to sell {shares_to_sell} shares @ ${current_price:.2f}")
            order = self.execute_order('sell', shares_to_sell)
            
            if order:
                self.trades.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'action': 'SELL',
                    'shares': shares_to_sell,
                    'price': current_price,
                    'status': str(order.status)
                })
                print(f"   Order ID: {order.id}\n")
        
        elif signal == "HOLD":
            print(f"⚪ HOLD - No action\n")
    
    def check_signal(self):
        """Check current signal and execute if needed"""
        
        if not self.fetch_price_data():
            return
        
        if len(self.prices_list) < 200:
            print("❌ Not enough data (need 200+ days)")
            return
        
        print("=" * 60)
        print(f"📊 SIGNAL CHECK: {self.ticker}")
        print("=" * 60)
        
        current_price = self.prices_list[-1]
        mas = self.calculate_moving_averages()
        signal = self.generate_signal()
        
        print(f"Current Price:      ${current_price:.2f}")
        print(f"50-day MA:          ${mas['short_ma']:.2f}")
        print(f"200-day MA:         ${mas['long_ma']:.2f}")
        print(f"Previous 50-day MA: ${mas['prev_short_ma']:.2f}")
        print(f"Previous 200-day MA: ${mas['prev_long_ma']:.2f}")
        print(f"\nSignal: {signal}")

        # BST analysis (inside method, so self works)
        min_price = self.price_tree.find_min() / 100
        max_price = self.price_tree.find_max() / 100

        print(f"\nBST Analysis:")
        print(f"  Min Price (BST): ${min_price:.2f}")
        print(f"  Max Price (BST): ${max_price:.2f}")
        print(f"  Total Nodes: {len(self.price_tree)}")

        account_info = self.get_account_info()
        if account_info:
            print(f"\nAccount:")
            print(f"  Equity: ${account_info['equity']:.2f}")
            print(f"  Cash: ${account_info['cash']:.2f}")

            position = self.get_position()
            if position:
                print(f"\nPosition:")
                print(f"  Shares: {position['qty']}")
                print(f"  Avg Price: ${position['avg_fill_price']:.2f}")
                print(f"  P&L: ${position['unrealized_pl']:.2f}")

        print("=" * 60 + "\n")

        self.execute_trade(signal, current_price)

    
    def run_backtest(self):
        """Run backtest on historical data"""

        if len(self.prices_list) < 200:
            print("❌ Not enough data for backtest")
            return

        print("\n" + "=" * 60)
        print(f"🤖 BACKTEST: {self.ticker}")
        print("=" * 60 + "\n")

        original_prices = self.prices_list[:]  # keep copy

        shares_held = 0
        cash = self.initial_capital
        trades = []

        for i in range(200, len(original_prices)):
            current_slice = original_prices[: i + 1]
            current_price = current_slice[-1]

            self.prices_list = current_slice
            signal = self.generate_signal()

            if signal == "BUY" and shares_held == 0:
                shares_to_buy = int(cash / current_price * 0.95)
                if shares_to_buy > 0:
                    cash -= shares_to_buy * current_price
                    shares_held = shares_to_buy
                    trades.append({"day": i, "action": "BUY", "price": current_price, "shares": shares_to_buy})
                    print(f"🟢 BUY: {shares_to_buy} @ ${current_price:.2f}")

            elif signal == "SELL" and shares_held > 0:
                cash += shares_held * current_price
                trades.append({"day": i, "action": "SELL", "price": current_price, "shares": shares_held})
                print(f"🔴 SELL: {shares_held} @ ${current_price:.2f}")
                shares_held = 0

        # restore full prices
        self.prices_list = original_prices

        final_price = original_prices[-1]
        portfolio_value = cash + (shares_held * final_price)
        total_return = ((portfolio_value - self.initial_capital) / self.initial_capital) * 100

        print("\n" + "=" * 60)
        print("📈 RESULTS")
        print("=" * 60)
        print(f"Initial Capital: ${self.initial_capital:.2f}")
        print(f"Portfolio Value: ${portfolio_value:.2f}")
        print(f"Total Return: {total_return:.2f}%")
        print(f"Total Trades: {len(trades)}")
        print("=" * 60 + "\n")
    
    def save_results(self, filename: str = "trading_results.json"):
        """Save results (signal + trades) to JSON"""

        mas = self.calculate_moving_averages() if len(self.prices_list) >= 200 else None
        signal = self.generate_signal() if len(self.prices_list) >= 200 else "Not enough data"
        current_price = self.prices_list[-1] if self.prices_list else None

        min_price = self.price_tree.find_min()
        max_price = self.price_tree.find_max()

        results = {
            "ticker": self.ticker,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_price": current_price,
            "signal": signal,
            "moving_averages": mas,
            "bst": {
                "min_price": (min_price / 100) if min_price is not None else None,
                "max_price": (max_price / 100) if max_price is not None else None,
                "total_nodes": len(self.price_tree),
            },
            "trades": self.trades,
        }

        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

        print(f"✅ Results saved to {filename}")




def main():
    """Main function"""
    
    try:
        # Create bot
        bot = SimpleTradingBot(ticker='AAPL', paper=True)
        
        # Fetch data
        bot.fetch_price_data(days=250)
        
        # Check signal
        bot.check_signal()
        
        # Optional: backtest
        # bot.run_backtest()
        
        # Save results
        bot.save_results()
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()