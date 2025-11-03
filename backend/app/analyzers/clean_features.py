#!/usr/bin/env python3
"""
Clean Features Module
Fix data leakage, NaNs, and feature engineering issues.
"""

import pandas as pd
import numpy as np
import talib
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

def clean_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and fix feature engineering issues.
    
    Fixes:
    1. Data leakage from NaN patterns
    2. Forward-fill price/volume with limits
    3. Proper technical indicator computation
    4. NaN indicator features
    5. Median filling instead of zero-filling
    6. Drop high-NaN features
    """
    logger.info(f"🧹 Cleaning features for {len(df)} rows...")
    
    # Make a copy to avoid modifying original
    df_clean = df.copy()
    
    # 1. Forward-fill price/volume (max 3 days to prevent stale data)
    price_volume_cols = ['open', 'high', 'low', 'close', 'volume']
    available_cols = [col for col in price_volume_cols if col in df_clean.columns]
    
    if available_cols:
        logger.info(f"📈 Forward-filling {len(available_cols)} price/volume columns (max 3 periods)")
        df_clean[available_cols] = df_clean[available_cols].ffill(limit=3)
    
    # 2. Recompute technical indicators with proper minimum periods
    if 'close' in df_clean.columns:
        logger.info("🔧 Recomputing technical indicators with proper min_periods...")
        
        # Moving averages - only compute where enough history
        df_clean['sma_5'] = df_clean['close'].rolling(5, min_periods=4).mean()
        df_clean['sma_10'] = df_clean['close'].rolling(10, min_periods=8).mean()
        df_clean['sma_20'] = df_clean['close'].rolling(20, min_periods=15).mean()
        
        # RSI with proper periods
        if len(df_clean) >= 14:
            df_clean['rsi_14'] = talib.RSI(df_clean['close'].values, timeperiod=14)
        if len(df_clean) >= 7:
            df_clean['rsi_7'] = talib.RSI(df_clean['close'].values, timeperiod=7)
        
        # MACD
        if len(df_clean) >= 26:
            macd, macd_signal, macd_hist = talib.MACD(df_clean['close'].values)
            df_clean['macd'] = macd
            df_clean['macd_signal'] = macd_signal
            df_clean['macd_histogram'] = macd_hist
        
        # Bollinger Bands
        if len(df_clean) >= 20:
            bb_upper, bb_middle, bb_lower = talib.BBANDS(df_clean['close'].values, timeperiod=20)
            df_clean['bb_upper'] = bb_upper
            df_clean['bb_middle'] = bb_middle
            df_clean['bb_lower'] = bb_lower
            
            # BB position (avoid division by zero)
            bb_range = bb_upper - bb_lower
            df_clean['bb_position'] = np.where(
                bb_range > 0,
                (df_clean['close'] - bb_lower) / bb_range,
                0.5  # Default to middle if range is zero
            )
        
        # Stochastic oscillator
        if len(df_clean) >= 14:
            stoch_k, stoch_d = talib.STOCH(
                df_clean['high'].values, 
                df_clean['low'].values, 
                df_clean['close'].values
            )
            df_clean['stoch_k'] = stoch_k
            df_clean['stoch_d'] = stoch_d
        
        # Williams %R
        if len(df_clean) >= 14:
            df_clean['williams_r'] = talib.WILLR(
                df_clean['high'].values,
                df_clean['low'].values, 
                df_clean['close'].values,
                timeperiod=14
            )
        
        # CCI
        if len(df_clean) >= 14:
            df_clean['cci'] = talib.CCI(
                df_clean['high'].values,
                df_clean['low'].values,
                df_clean['close'].values,
                timeperiod=14
            )
        
        # ATR
        if len(df_clean) >= 14:
            df_clean['atr_14'] = talib.ATR(
                df_clean['high'].values,
                df_clean['low'].values,
                df_clean['close'].values,
                timeperiod=14
            )
    
    # 3. Fix volume ratio with proper lagging to prevent leakage
    if 'volume' in df_clean.columns:
        logger.info("📊 Computing lagged volume indicators...")
        
        # Volume SMA with lag to prevent leakage
        df_clean['volume_sma_10'] = df_clean['volume'].shift(1).rolling(10, min_periods=8).mean()
        
        # Volume ratio using lagged SMA
        df_clean['volume_ratio'] = np.where(
            df_clean['volume_sma_10'] > 0,
            df_clean['volume'] / df_clean['volume_sma_10'],
            1.0  # Default ratio if no history
        )
        
        # Volume trend (lagged)
        volume_5d_ago = df_clean['volume'].shift(5)
        df_clean['volume_trend'] = np.where(
            volume_5d_ago > 0,
            (df_clean['volume'] - volume_5d_ago) / volume_5d_ago,
            0.0
        )
    
    # 4. Add NaN indicator features (model learns "missing" is not a signal)
    nan_indicator_features = [
        'sma_20', 'rsi_14', 'rsi_7', 'macd', 'macd_signal', 'macd_histogram',
        'bb_upper', 'bb_middle', 'bb_lower', 'stoch_k', 'stoch_d',
        'williams_r', 'cci', 'atr_14', 'volume_ratio'
    ]
    
    logger.info("🚩 Adding NaN indicator features...")
    for col in nan_indicator_features:
        if col in df_clean.columns:
            df_clean[f'{col}_isnan'] = df_clean[col].isna().astype(int)
    
    # 5. Drop features with >80% NaN (they're not useful)
    high_nan_threshold = 0.8
    high_nan_cols = []
    
    for col in df_clean.columns:
        if df_clean[col].dtype in ['float64', 'int64']:  # Only check numeric columns
            nan_pct = df_clean[col].isna().mean()
            if nan_pct > high_nan_threshold:
                high_nan_cols.append(col)
    
    if high_nan_cols:
        logger.warning(f"🗑️  Dropping {len(high_nan_cols)} high-NaN features: {high_nan_cols}")
        df_clean = df_clean.drop(columns=high_nan_cols)
    
    # 6. Fill remaining NaNs with MEDIAN (not zero!) to prevent bias
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
    
    logger.info("🔢 Filling remaining NaNs with median values...")
    for col in numeric_cols:
        if df_clean[col].isna().any():
            median_val = df_clean[col].median()
            if pd.isna(median_val):  # If all values are NaN, use 0
                median_val = 0.0
            df_clean[col] = df_clean[col].fillna(median_val)
    
    # 7. Add derived features that are less prone to leakage
    if all(col in df_clean.columns for col in ['close', 'open', 'high', 'low']):
        logger.info("📊 Adding derived price features...")
        
        # Price ratios
        df_clean['high_low_ratio'] = df_clean['high'] / df_clean['low'].replace(0, np.nan)
        df_clean['close_open_ratio'] = df_clean['close'] / df_clean['open'].replace(0, np.nan)
        
        # SMA ratios (with lag to prevent leakage)
        for sma_period in [5, 10, 20]:
            sma_col = f'sma_{sma_period}'
            ratio_col = f'close_sma{sma_period}_ratio'
            if sma_col in df_clean.columns:
                df_clean[ratio_col] = df_clean['close'] / df_clean[sma_col].replace(0, np.nan)
        
        # Momentum (rate of change) with proper lagging
        df_clean['momentum_5'] = df_clean['close'].pct_change(5) * 100
        df_clean['momentum_10'] = df_clean['close'].pct_change(10) * 100
        df_clean['roc_5'] = df_clean['momentum_5']  # Same as momentum
        df_clean['roc_10'] = df_clean['momentum_10']
        
        # Volatility (rolling std of returns)
        returns = df_clean['close'].pct_change()
        df_clean['volatility_10'] = returns.rolling(10, min_periods=5).std()
        df_clean['recent_volatility'] = returns.rolling(5, min_periods=3).std()
        
        # Price trend percentage
        close_5d_ago = df_clean['close'].shift(5)
        df_clean['price_trend_pct'] = np.where(
            close_5d_ago > 0,
            (df_clean['close'] - close_5d_ago) / close_5d_ago * 100,
            0.0
        )
        
        # Gap percentage (today's open vs yesterday's close)
        prev_close = df_clean['close'].shift(1)
        df_clean['gap_pct'] = np.where(
            prev_close > 0,
            (df_clean['open'] - prev_close) / prev_close * 100,
            0.0
        )
    
    # Final cleanup - replace any remaining inf values
    df_clean = df_clean.replace([np.inf, -np.inf], np.nan)
    
    # Fill any new NaNs created by ratios
    for col in numeric_cols:
        if col in df_clean.columns and df_clean[col].isna().any():
            median_val = df_clean[col].median()
            if pd.isna(median_val):
                median_val = 0.0
            df_clean[col] = df_clean[col].fillna(median_val)
    
    logger.info(f"✅ Feature cleaning complete: {len(df_clean)} rows, {len(df_clean.columns)} features")
    
    return df_clean

def validate_features(df: pd.DataFrame) -> Dict[str, any]:
    """Validate cleaned features for quality."""
    validation_results = {
        'total_rows': len(df),
        'total_features': len(df.columns),
        'nan_count': df.isna().sum().sum(),
        'inf_count': np.isinf(df.select_dtypes(include=[np.number])).sum().sum(),
        'high_nan_features': [],
        'constant_features': [],
        'feature_ranges': {}
    }
    
    # Check for remaining issues
    for col in df.select_dtypes(include=[np.number]).columns:
        nan_pct = df[col].isna().mean()
        if nan_pct > 0.1:  # More than 10% NaN
            validation_results['high_nan_features'].append((col, nan_pct))
        
        if df[col].nunique() <= 1:  # Constant feature
            validation_results['constant_features'].append(col)
        
        validation_results['feature_ranges'][col] = {
            'min': df[col].min(),
            'max': df[col].max(),
            'median': df[col].median()
        }
    
    return validation_results
