#!/bin/bash

# BullsBears Phase 2 Setup Script
# Installs dependencies and sets up data collection pipeline

echo "🚀 BullsBears Phase 2 Setup - Historical Data Collection"
echo "========================================================"

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/backtest
mkdir -p models
mkdir -p logs

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install yfinance==0.2.28
pip install databento==0.36.0

# Optional: Install TA-Lib (requires system dependencies)
echo "🔧 Checking TA-Lib installation..."
python -c "import talib" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ TA-Lib is already installed"
else
    echo "⚠️  TA-Lib not found. Installing..."
    
    # Detect OS and install TA-Lib accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "🍎 Detected macOS - installing TA-Lib via Homebrew..."
        if command -v brew &> /dev/null; then
            brew install ta-lib
            pip install TA-Lib
        else
            echo "❌ Homebrew not found. Please install TA-Lib manually:"
            echo "   1. Install Homebrew: https://brew.sh/"
            echo "   2. Run: brew install ta-lib"
            echo "   3. Run: pip install TA-Lib"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "🐧 Detected Linux - installing TA-Lib..."
        sudo apt-get update
        sudo apt-get install -y build-essential
        wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
        tar -xzf ta-lib-0.4.0-src.tar.gz
        cd ta-lib/
        ./configure --prefix=/usr
        make
        sudo make install
        cd ..
        rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
        pip install TA-Lib
    else
        echo "❌ Unsupported OS. Please install TA-Lib manually:"
        echo "   Visit: https://github.com/mrjbq7/ta-lib#installation"
    fi
fi

# Verify installations
echo "🔍 Verifying installations..."

python -c "import yfinance; print('✅ yfinance installed successfully')" 2>/dev/null || echo "❌ yfinance installation failed"

python -c "import databento; print('✅ databento installed successfully')" 2>/dev/null || echo "⚠️  databento installation failed (optional)"

python -c "import talib; print('✅ TA-Lib installed successfully')" 2>/dev/null || echo "⚠️  TA-Lib installation failed (required for technical analysis)"

python -c "import pandas, numpy; print('✅ pandas/numpy available')" 2>/dev/null || echo "❌ pandas/numpy missing"

# Check for NASDAQ data file
echo "📊 Checking for NASDAQ data file..."
if [ -f "../Data/nasdaq_screener_1762100638908.csv" ]; then
    echo "✅ NASDAQ screener data found"
else
    echo "⚠️  NASDAQ screener data not found at ../Data/nasdaq_screener_1762100638908.csv"
    echo "   Please ensure the file is in the correct location"
fi

# Check environment variables
echo "🔑 Checking environment variables..."
if [ -f ".env" ]; then
    echo "✅ .env file found"
    
    # Check for required API keys
    if grep -q "DATABENTO_API_KEY" .env; then
        echo "✅ DATABENTO_API_KEY configured"
    else
        echo "⚠️  DATABENTO_API_KEY not found in .env (optional but recommended)"
        echo "   Add: DATABENTO_API_KEY=your_key_here"
    fi
    
    if grep -q "ALPHA_VANTAGE_API_KEY" .env; then
        echo "✅ ALPHA_VANTAGE_API_KEY configured"
    else
        echo "⚠️  ALPHA_VANTAGE_API_KEY not found in .env"
    fi
else
    echo "❌ .env file not found. Please create one with required API keys"
fi

# Test the data pipeline
echo "🧪 Testing data pipeline components..."

echo "   Testing ticker processor..."
python -c "
import sys
sys.path.append('app')
from app.analyzers.ticker_processor import TickerProcessor
processor = TickerProcessor()
print('✅ Ticker processor imports successfully')
" 2>/dev/null || echo "❌ Ticker processor test failed"

echo "   Testing data downloader..."
python -c "
import sys
sys.path.append('app')
from app.analyzers.data_downloader import DataDownloader
downloader = DataDownloader()
print('✅ Data downloader imports successfully')
" 2>/dev/null || echo "❌ Data downloader test failed"

echo "   Testing move detector..."
python -c "
import sys
sys.path.append('app')
from app.analyzers.move_detector import MoveDetector
detector = MoveDetector()
print('✅ Move detector imports successfully')
" 2>/dev/null || echo "❌ Move detector test failed"

# Database migration reminder
echo "💾 Database setup reminder..."
if [ -f "../migrations/add_moon_rug_fields.sql" ]; then
    echo "✅ Database migration file found"
    echo "   Run: psql -d bullsbears -f ../migrations/add_moon_rug_fields.sql"
else
    echo "⚠️  Database migration file not found"
fi

echo ""
echo "🎯 Phase 2 Setup Complete!"
echo "=========================="
echo ""
echo "📝 Next Steps:"
echo "   1. Ensure database migration is applied"
echo "   2. Run ticker processing: python test_data_pipeline.py --step 1"
echo "   3. Run data download: python test_data_pipeline.py --step 2 --sample"
echo "   4. Run move detection: python test_data_pipeline.py --step 3"
echo "   5. Run full pipeline: python test_data_pipeline.py"
echo ""
echo "🔬 For testing with limited data:"
echo "   python test_data_pipeline.py --sample"
echo ""
echo "📚 Documentation:"
echo "   See: PHASE2_IMPLEMENTATION.md for detailed setup guide"
echo ""

# Make the test script executable
chmod +x test_data_pipeline.py

echo "✅ Setup script completed successfully!"
