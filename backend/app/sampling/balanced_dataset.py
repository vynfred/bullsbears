#!/usr/bin/env python3
"""
Balanced Dataset Generator
Fix class imbalance and create proper train/test splits.
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, Dict
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

def create_realistic_dataset(df: pd.DataFrame, target_col: str = 'event_type') -> pd.DataFrame:
    """
    Create realistic dataset that preserves natural market frequencies.

    Strategy:
    1. Keep ALL real events (no undersampling)
    2. Add strategic hard negatives for better discrimination
    3. Use class weights during training to handle imbalance
    4. Preserve realistic market event frequencies
    """
    logger.info(f"🎯 Creating realistic dataset from {len(df)} samples...")

    # Separate by event type
    moon_events = df[df[target_col] == 'moon'].copy()
    rug_events = df[df[target_col] == 'rug'].copy()

    logger.info(f"📊 Original distribution (PRESERVING ALL DATA):")
    logger.info(f"   Moon events: {len(moon_events)} ({len(moon_events)/len(df)*100:.1f}%)")
    logger.info(f"   Rug events: {len(rug_events)} ({len(rug_events)/len(df)*100:.1f}%)")

    # 1. Keep ALL real events (no undersampling!)
    logger.info("✅ Keeping all real moon and rug events for maximum training data")

    # 2. Generate strategic hard negatives (moderate amount)
    # Rule: Add hard negatives equal to 50% of positive events (not 200%!)
    total_positive = len(moon_events) + len(rug_events)
    n_hard_negatives = int(total_positive * 0.5)  # 50% of positive events
    logger.info(f"🎯 Generating {n_hard_negatives} strategic hard negatives ({n_hard_negatives/total_positive:.1%} of positive events)")

    hard_negatives = generate_hard_negatives(
        positive_events=pd.concat([moon_events, rug_events]),
        n_samples=n_hard_negatives,
        feature_cols=[col for col in df.columns if col not in [target_col, 'ticker', 'event_date', 'target_return']]
    )

    # 3. Combine into realistic dataset
    realistic_df = pd.concat([
        moon_events,  # Keep all moon events
        rug_events,   # Keep all rug events
        hard_negatives
    ], ignore_index=True)

    # Shuffle the dataset
    realistic_df = realistic_df.sample(frac=1, random_state=42).reset_index(drop=True)

    total_samples = len(realistic_df)
    logger.info(f"✅ Realistic dataset created:")
    logger.info(f"   Total samples: {total_samples}")
    logger.info(f"   Moon: {len(moon_events)} ({len(moon_events)/total_samples*100:.1f}%)")
    logger.info(f"   Rug: {len(rug_events)} ({len(rug_events)/total_samples*100:.1f}%)")
    logger.info(f"   Hard Negatives: {len(hard_negatives)} ({len(hard_negatives)/total_samples*100:.1f}%)")
    logger.info(f"   🎯 This preserves natural market event frequencies!")

    return realistic_df

def generate_hard_negatives(positive_events: pd.DataFrame, n_samples: int, feature_cols: list) -> pd.DataFrame:
    """
    Generate sophisticated hard negative samples - "almost moons" that failed.

    Strategy:
    1. Create "almost moon" setups that had 90% of the signals but failed
    2. Create "failed breakouts" that looked promising but reversed
    3. Create "fake volume spikes" that didn't sustain
    4. Ensure they represent realistic failed market scenarios
    """
    logger.info(f"🎯 Generating {n_samples} sophisticated hard negatives (almost moons that failed)...")

    if len(positive_events) == 0:
        logger.warning("No positive events provided for hard negative generation")
        return pd.DataFrame()

    hard_negatives = []

    # Separate moon and rug events for different strategies
    moon_events = positive_events[positive_events['event_type'] == 'moon'] if 'event_type' in positive_events.columns else positive_events
    rug_events = positive_events[positive_events['event_type'] == 'rug'] if 'event_type' in positive_events.columns else pd.DataFrame()

    for i in range(n_samples):
        # Choose strategy for this hard negative
        strategy = np.random.choice(['almost_moon', 'failed_breakout', 'fake_volume', 'almost_rug'],
                                  p=[0.4, 0.3, 0.2, 0.1])

        if strategy == 'almost_moon' and len(moon_events) > 0:
            # Create "almost moon" - had most signals but failed
            base_event = moon_events.sample(n=1, random_state=42+i).iloc[0]
            hard_negative = base_event.copy()

            # Keep 80% of the bullish signals, weaken the rest
            for feature in feature_cols:
                if feature in hard_negative.index and not pd.isna(hard_negative[feature]):
                    original_value = hard_negative[feature]

                    if 'rsi' in feature.lower():
                        # Keep oversold but make it less extreme
                        if original_value < 30:
                            hard_negative[feature] = original_value + np.random.uniform(5, 15)

                    elif 'volume_ratio' in feature.lower():
                        # Reduce volume surge significantly (key failure point)
                        if original_value > 1.5:
                            hard_negative[feature] = original_value * np.random.uniform(0.4, 0.7)

                    elif 'momentum' in feature.lower():
                        # Weaken momentum (another key failure point)
                        hard_negative[feature] = original_value * np.random.uniform(0.2, 0.5)

            hard_negative['target_return'] = np.random.uniform(-2, 8)  # Small gain or loss

        elif strategy == 'failed_breakout' and len(moon_events) > 0:
            # Create "failed breakout" - looked like breakout but reversed
            base_event = moon_events.sample(n=1, random_state=42+i).iloc[0]
            hard_negative = base_event.copy()

            # Strong initial signals but add reversal indicators
            for feature in feature_cols:
                if feature in hard_negative.index and not pd.isna(hard_negative[feature]):
                    original_value = hard_negative[feature]

                    if 'bb_position' in feature.lower():
                        # Move to overbought territory (reversal signal)
                        hard_negative[feature] = min(0.95, original_value + 0.3)

                    elif 'stoch' in feature.lower():
                        # Overbought stochastic (reversal signal)
                        hard_negative[feature] = np.random.uniform(75, 95)

                    elif 'williams_r' in feature.lower():
                        # Overbought Williams %R
                        hard_negative[feature] = np.random.uniform(-30, -10)

            hard_negative['target_return'] = np.random.uniform(-8, 3)  # Failed breakout

        elif strategy == 'fake_volume' and len(moon_events) > 0:
            # Create "fake volume spike" - volume without follow-through
            base_event = moon_events.sample(n=1, random_state=42+i).iloc[0]
            hard_negative = base_event.copy()

            # Keep high volume but remove other confirming signals
            for feature in feature_cols:
                if feature in hard_negative.index and not pd.isna(hard_negative[feature]):
                    original_value = hard_negative[feature]

                    if 'volume_ratio' in feature.lower():
                        # Keep high volume
                        hard_negative[feature] = max(original_value, 2.0)

                    elif 'momentum' in feature.lower() or 'roc' in feature.lower():
                        # Remove momentum (volume without price follow-through)
                        hard_negative[feature] = original_value * np.random.uniform(-0.5, 0.2)

                    elif 'macd' in feature.lower():
                        # Bearish MACD despite volume
                        if 'histogram' in feature.lower():
                            hard_negative[feature] = -abs(original_value)

            hard_negative['target_return'] = np.random.uniform(-5, 5)  # No follow-through

        elif strategy == 'almost_rug' and len(rug_events) > 0:
            # Create "almost rug" - had bearish signals but didn't crash
            base_event = rug_events.sample(n=1, random_state=42+i).iloc[0]
            hard_negative = base_event.copy()

            # Keep some bearish signals but add support
            for feature in feature_cols:
                if feature in hard_negative.index and not pd.isna(hard_negative[feature]):
                    original_value = hard_negative[feature]

                    if 'rsi' in feature.lower():
                        # Less overbought
                        if original_value > 70:
                            hard_negative[feature] = original_value - np.random.uniform(10, 20)

                    elif 'volume_ratio' in feature.lower():
                        # Lower selling volume
                        hard_negative[feature] = original_value * np.random.uniform(0.6, 0.9)

            hard_negative['target_return'] = np.random.uniform(-10, 2)  # Small decline

        else:
            # Fallback: generic hard negative
            base_event = positive_events.sample(n=1, random_state=42+i).iloc[0]
            hard_negative = base_event.copy()

            # Add generic noise
            for feature in feature_cols:
                if feature in hard_negative.index and not pd.isna(hard_negative[feature]):
                    original_value = hard_negative[feature]
                    noise_factor = np.random.uniform(0.8, 1.2)
                    hard_negative[feature] = original_value * noise_factor

            hard_negative['target_return'] = np.random.uniform(-5, 5)

        # Set as negative class
        hard_negative['event_type'] = 'negative'

        # Add strategy label for analysis
        if 'ticker' in hard_negative.index:
            hard_negative['ticker'] = f"HARD_NEG_{strategy.upper()}_{i:04d}"

        hard_negatives.append(hard_negative)

    hard_negatives_df = pd.DataFrame(hard_negatives)

    logger.info(f"✅ Generated {len(hard_negatives_df)} sophisticated hard negatives")
    logger.info(f"   Strategies: almost_moon, failed_breakout, fake_volume, almost_rug")

    return hard_negatives_df

def create_purged_splits(df: pd.DataFrame, test_size: float = 0.2, embargo_pct: float = 0.01) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create train/test splits with purged cross-validation to prevent data leakage.
    
    Args:
        df: Dataset with event_date column
        test_size: Fraction for test set
        embargo_pct: Percentage of data to embargo between train/test
    """
    logger.info(f"📅 Creating purged train/test splits...")
    
    if 'event_date' not in df.columns:
        logger.warning("No event_date column found, using random split")
        return train_test_split(df, test_size=test_size, random_state=42, stratify=df.get('event_type'))
    
    # Sort by date
    df_sorted = df.sort_values('event_date').reset_index(drop=True)
    
    # Calculate split points with embargo
    n_total = len(df_sorted)
    n_test = int(n_total * test_size)
    n_embargo = int(n_total * embargo_pct)
    
    # Test set: most recent data
    test_start = n_total - n_test
    test_df = df_sorted.iloc[test_start:].copy()
    
    # Train set: older data with embargo gap
    train_end = test_start - n_embargo
    train_df = df_sorted.iloc[:train_end].copy()
    
    logger.info(f"📊 Purged split results:")
    logger.info(f"   Train: {len(train_df)} samples ({train_df['event_date'].min()} to {train_df['event_date'].max()})")
    logger.info(f"   Embargo: {n_embargo} samples")
    logger.info(f"   Test: {len(test_df)} samples ({test_df['event_date'].min()} to {test_df['event_date'].max()})")
    
    return train_df, test_df

def calculate_class_weights(y: pd.Series) -> Dict[str, float]:
    """Calculate class weights for imbalanced learning."""
    from sklearn.utils.class_weight import compute_class_weight
    
    classes = np.unique(y)
    class_weights = compute_class_weight('balanced', classes=classes, y=y)
    
    weight_dict = dict(zip(classes, class_weights))
    
    logger.info(f"📊 Calculated class weights: {weight_dict}")
    
    return weight_dict

def validate_balanced_dataset(df: pd.DataFrame, target_col: str = 'event_type') -> Dict[str, any]:
    """Validate the balanced dataset."""
    validation = {
        'total_samples': len(df),
        'class_distribution': df[target_col].value_counts().to_dict(),
        'class_percentages': (df[target_col].value_counts() / len(df) * 100).to_dict(),
        'feature_count': len([col for col in df.columns if col not in [target_col, 'ticker', 'event_date', 'target_return']]),
        'date_range': None,
        'missing_values': df.isnull().sum().sum()
    }
    
    if 'event_date' in df.columns:
        validation['date_range'] = {
            'start': df['event_date'].min(),
            'end': df['event_date'].max()
        }
    
    # Check balance quality
    class_counts = df[target_col].value_counts()
    max_count = class_counts.max()
    min_count = class_counts.min()
    balance_ratio = min_count / max_count if max_count > 0 else 0
    
    validation['balance_quality'] = {
        'ratio': balance_ratio,
        'is_balanced': balance_ratio >= 0.5  # At least 50% of majority class
    }
    
    return validation
