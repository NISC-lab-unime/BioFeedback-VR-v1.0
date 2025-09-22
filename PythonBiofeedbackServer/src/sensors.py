#!/usr/bin/env python3
"""
Biofeedback Sensors Module
==========================

Provides realistic HR and EDA signal generation for the cybertherapy biofeedback demo.
Refactored from Phase 1 simulator to provide clean API functions.

Based on research from:
- Lucifora et al. (2021) - Cyber-Therapy with biofeedback signals  
- Moldoveanu et al. (2023) - Immersive Phobia Therapy through Adaptive VR

Date: August 2025
"""

import numpy as np
import time
from typing import Tuple

# Global state for simulation continuity
_current_time = 0
_base_hr = 75.0      # Baseline heart rate in BPM
_base_eda = 2.0      # Baseline EDA in microsiemens
_scenario = "mixed"  # Current scenario: baseline, stress_buildup, recovery, mixed

# HRV tracking state
_hr_history = []     # Recent HR values for HRV calculation
_hrv_window_size = 20  # Number of HR samples to keep for HRV calculation

# Baseline protocol state
_baseline_computed = False    # Whether baseline values have been computed
_baseline_hr = 75.0          # Computed baseline HR (BPM)
_baseline_eda = 2.0          # Computed baseline EDA (µS)
_baseline_hrv = 50.0         # Computed baseline HRV (ms)
_baseline_samples = []       # Samples collected during baseline period
_baseline_window_seconds = 60  # Duration for baseline computation
_resting_period_seconds = 180  # 3-minute resting period (180s)

def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value between min and max bounds.
    
    Args:
        value: Input value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))

def get_hr() -> float:
    """
    Generate realistic heart rate value for current time.
    
    Uses sinusoidal variations with physiological noise to simulate natural
    heart rate variability (HRV). Produces values typically between 60-120 BPM
    based on the current scenario.
    
    Calibration parameters from Phase 1 analysis:
    - Baseline: 75 BPM with ±3 BPM slow variation (45s cycle)
    - Fast variation: ±2 BPM (12s cycle, simulates breathing)
    - Noise: Gaussian with σ=1.5 BPM
    - Stress response: Up to +20 BPM during stress scenarios
    
    Returns:
        Heart rate in beats per minute (BPM)
    """
    global _current_time, _base_hr, _scenario
    
    t = _current_time
    
    if _scenario == "baseline":
        # Calm baseline with natural HRV
        base = _base_hr
        slow_variation = 3 * np.sin(2 * np.pi * t / 45)  # ~45s cycle
        fast_variation = 2 * np.sin(2 * np.pi * t / 12)  # ~12s cycle (breathing)
        noise = np.random.normal(0, 1.5)
        
    elif _scenario == "stress_buildup":
        # Gradual stress increase over 30 seconds
        stress_factor = min(t / 30, 1.0)  # Build up over 30 seconds
        base = _base_hr + stress_factor * 20  # Up to +20 BPM
        slow_variation = 2 * np.sin(2 * np.pi * t / 30)
        fast_variation = 3 * np.sin(2 * np.pi * t / 8)   # Faster breathing
        noise = np.random.normal(0, 2 + stress_factor)   # More variability when stressed
        
    elif _scenario == "recovery":
        # Recovery from stress
        if t < 10:
            stress_factor = 1.0 - (t / 10)  # Reduce stress over first 10s
            base = _base_hr + stress_factor * 15
            slow_variation = 3 * np.sin(2 * np.pi * t / 25)
            fast_variation = 2 * np.sin(2 * np.pi * t / 10)
            noise = np.random.normal(0, 2)
        else:
            # Calm recovery phase
            base = _base_hr
            slow_variation = 2 * np.sin(2 * np.pi * t / 40)
            fast_variation = 1.5 * np.sin(2 * np.pi * t / 12)
            noise = np.random.normal(0, 1.2)
            
    else:  # "mixed" scenario (default)
        # Combined scenario: calm -> stress -> recovery
        if t < 20:
            # Calm phase (0-20s)
            base = _base_hr
            slow_variation = 3 * np.sin(2 * np.pi * t / 45)
            fast_variation = 2 * np.sin(2 * np.pi * t / 12)
            noise = np.random.normal(0, 1.5)
        elif t < 40:
            # Stress phase (20-40s)
            stress_factor = (t - 20) / 20  # Build stress over 20s
            base = _base_hr + stress_factor * 25
            slow_variation = 4 * np.sin(2 * np.pi * t / 20)
            fast_variation = 3 * np.sin(2 * np.pi * t / 6)   # Rapid breathing
            noise = np.random.normal(0, 2.5 + stress_factor)
        else:
            # Recovery phase (40s+)
            recovery_factor = min((t - 40) / 20, 1.0)
            base = _base_hr + (1 - recovery_factor) * 20  # Gradual return to baseline
            slow_variation = 2 * np.sin(2 * np.pi * t / 35)
            fast_variation = 2 * np.sin(2 * np.pi * t / 12)
            noise = np.random.normal(0, 1.8)
    
    hr = base + slow_variation + fast_variation + noise
    
    # Clamp to physiological limits (50-180 BPM)
    hr = clamp(hr, 50.0, 180.0)
    
    # Track HR history for HRV calculation
    global _hr_history, _hrv_window_size
    _hr_history.append(hr)
    
    # Keep only the most recent samples for HRV calculation
    if len(_hr_history) > _hrv_window_size:
        _hr_history = _hr_history[-_hrv_window_size:]
    
    return hr

def get_eda() -> float:
    """
    Generate realistic electrodermal activity (EDA) value for current time.
    
    Simulates skin conductance changes that correlate with autonomic arousal.
    Produces values typically between 0.5-5 µS based on scenario.
    
    Calibration parameters from Phase 1 analysis:
    - Baseline: 2.0 µS with smooth variations
    - Slower response than HR (15-60s cycles)
    - Stress response: Up to +100% increase during stress
    - More gradual changes than HR (reflects sweat gland response)
    
    Returns:
        EDA value in microsiemens (µS)
    """
    global _current_time, _base_eda, _scenario
    
    t = _current_time
    
    if _scenario == "baseline":
        # Calm baseline with gentle variations
        base = _base_eda
        slow_variation = 0.3 * np.sin(2 * np.pi * t / 60)  # ~60s cycle
        medium_variation = 0.2 * np.sin(2 * np.pi * t / 25)  # ~25s cycle
        noise = np.random.normal(0, 0.1)
        
    elif _scenario == "stress_buildup":
        # Gradual EDA increase (slower than HR response)
        stress_factor = min(t / 45, 1.0)  # Build up over 45s (slower than HR)
        base = _base_eda + stress_factor * 2.0  # Up to +2 µS
        slow_variation = 0.4 * np.sin(2 * np.pi * t / 40)
        medium_variation = 0.3 * np.sin(2 * np.pi * t / 15)
        noise = np.random.normal(0, 0.15 + stress_factor * 0.1)
        
    elif _scenario == "recovery":
        # Slow recovery (EDA takes longer to return to baseline)
        if t < 20:
            stress_factor = 1.0 - (t / 20)  # Slow decrease over 20s
            base = _base_eda + stress_factor * 1.8
            slow_variation = 0.4 * np.sin(2 * np.pi * t / 35)
            medium_variation = 0.25 * np.sin(2 * np.pi * t / 18)
            noise = np.random.normal(0, 0.12)
        else:
            # Calm recovery
            base = _base_eda
            slow_variation = 0.25 * np.sin(2 * np.pi * t / 55)
            medium_variation = 0.15 * np.sin(2 * np.pi * t / 28)
            noise = np.random.normal(0, 0.08)
            
    else:  # "mixed" scenario (default)
        # Combined scenario: calm -> stress -> recovery
        if t < 20:
            # Calm phase (0-20s)
            base = _base_eda
            slow_variation = 0.3 * np.sin(2 * np.pi * t / 60)
            medium_variation = 0.2 * np.sin(2 * np.pi * t / 25)
            noise = np.random.normal(0, 0.1)
        elif t < 40:
            # Stress phase (20-40s) - EDA rises more slowly than HR
            stress_factor = (t - 20) / 30  # Slower buildup than HR
            base = _base_eda + stress_factor * 2.5  # Higher peak than single stress
            slow_variation = 0.5 * np.sin(2 * np.pi * t / 30)
            medium_variation = 0.4 * np.sin(2 * np.pi * t / 12)
            noise = np.random.normal(0, 0.2 + stress_factor * 0.1)
        else:
            # Recovery phase (40s+) - EDA takes longer to recover
            recovery_factor = min((t - 40) / 30, 1.0)  # Longer recovery than HR
            base = _base_eda + (1 - recovery_factor) * 2.2
            slow_variation = 0.35 * np.sin(2 * np.pi * t / 45)
            medium_variation = 0.25 * np.sin(2 * np.pi * t / 20)
            noise = np.random.normal(0, 0.12)
    
    eda = base + slow_variation + medium_variation + noise
    
    # Clamp to physiological limits (0.1-10 µS)
    eda = clamp(eda, 0.1, 10.0)
    
    return eda

def get_hrv() -> float:
    """
    Calculate Heart Rate Variability (HRV) using SDNN method.
    
    SDNN (Standard Deviation of NN intervals) measures the variation between
    consecutive heartbeats. Higher HRV typically indicates better autonomic
    nervous system balance and lower stress.
    
    Returns:
        HRV value (SDNN) in milliseconds. Returns 50.0 if insufficient data.
    """
    global _hr_history
    
    if len(_hr_history) < 2:
        # Insufficient data for HRV calculation - return typical resting HRV
        return 50.0
    
    # Convert HR (BPM) to RR intervals (milliseconds)
    # RR interval = 60000 / HR (since 60 seconds = 60000 ms)
    rr_intervals = [60000 / hr for hr in _hr_history]
    
    # Calculate differences between consecutive RR intervals (NN intervals)
    nn_intervals = [abs(rr_intervals[i+1] - rr_intervals[i]) for i in range(len(rr_intervals)-1)]
    
    if len(nn_intervals) == 0:
        return 50.0
    
    # Calculate SDNN (standard deviation of NN intervals)
    mean_nn = sum(nn_intervals) / len(nn_intervals)
    variance = sum((nn - mean_nn) ** 2 for nn in nn_intervals) / len(nn_intervals)
    sdnn = variance ** 0.5
    
    # Clamp to physiological range (10-200 ms for SDNN)
    sdnn = clamp(sdnn, 10.0, 200.0)
    
    return sdnn

def compute_stress_index(hr: float, eda: float, hrv: float = None, w_hr: float = 0.33, w_eda: float = 0.33, w_hrv: float = 0.34) -> float:
    """
    Compute 0-100 stress index from HR, EDA, and HRV values.
    
    Normalizes physiological signals to a common scale and combines them
    using weighted averaging to produce a stress index from 0 (calm) to 100 (highly stressed).
    
    Normalization assumptions:
    - HR range: 45-180 BPM (45 = deep relaxation, 180 = maximum exercise)
    - EDA range: 0-10 µS (0 = completely dry, 10 = maximum arousal)
    - HRV range: 10-200 ms SDNN (higher HRV = lower stress, so inverted)
    - Linear scaling within these ranges
    
    Args:
        hr: Heart rate in BPM
        eda: Electrodermal activity in µS  
        hrv: Heart rate variability (SDNN) in ms (optional - computed if None)
        w_hr: Weight for HR contribution (default: 0.33)
        w_eda: Weight for EDA contribution (default: 0.33)
        w_hrv: Weight for HRV contribution (default: 0.34)
        
    Returns:
        Stress index from 0-100
    """
    # Get HRV if not provided
    if hrv is None:
        hrv = get_hrv()
    
    # Normalize HR from 45-180 BPM to 0-1 range (higher HR = higher stress)
    norm_hr = clamp((hr - 45) / (180 - 45), 0, 1)
    
    # Normalize EDA from 0-10 µS to 0-1 range (higher EDA = higher stress)
    norm_eda = clamp(eda / 10, 0, 1)
    
    # Normalize HRV from 10-200 ms to 0-1 range (INVERTED: higher HRV = lower stress)
    norm_hrv = clamp(1.0 - ((hrv - 10) / (200 - 10)), 0, 1)
    
    # Weighted combination scaled to 0-100
    stress_index = (w_hr * norm_hr + w_eda * norm_eda + w_hrv * norm_hrv) * 100
    
    return stress_index

def _advance_time(dt: float = 1.0) -> None:
    """Advance the internal simulation time by dt seconds.
    
    Args:
        dt: Time delta in seconds (default: 1.0 for backward compatibility)
    """
    global _current_time
    _current_time += dt

def _reset_time() -> None:
    """Reset the internal simulation time to 0."""
    global _current_time
    _current_time = 0

def set_scenario(scenario: str) -> None:
    """
    Set the simulation scenario.
    
    Args:
        scenario: One of 'baseline', 'stress_buildup', 'recovery', 'mixed'
    """
    global _scenario
    valid_scenarios = ['baseline', 'stress_buildup', 'recovery', 'mixed']
    if scenario in valid_scenarios:
        _scenario = scenario
    else:
        raise ValueError(f"Invalid scenario. Choose from: {valid_scenarios}")

def get_current_time() -> int:
    """Get the current simulation time in seconds."""
    return _current_time

def get_current_scenario() -> str:
    """Get the current simulation scenario."""
    return _scenario

# ============================================================================
# Baseline Protocol Functions
# ============================================================================

def is_in_resting_period() -> bool:
    """Check if the simulation is still in the resting period."""
    global _current_time, _resting_period_seconds
    return _current_time < _resting_period_seconds

def is_in_baseline_window() -> bool:
    """Check if the simulation is in the baseline computation window."""
    global _current_time, _resting_period_seconds, _baseline_window_seconds
    baseline_start = _resting_period_seconds
    baseline_end = _resting_period_seconds + _baseline_window_seconds
    return baseline_start <= _current_time < baseline_end

def should_collect_baseline_sample() -> bool:
    """Check if a baseline sample should be collected at current time."""
    return is_in_baseline_window() and not _baseline_computed

def collect_baseline_sample(hr: float, eda: float, hrv: float) -> None:
    """Collect a sample during the baseline computation window."""
    global _baseline_samples
    
    sample = {
        'time': _current_time,
        'hr': hr,
        'eda': eda,
        'hrv': hrv
    }
    _baseline_samples.append(sample)

def compute_baseline_values() -> bool:
    """Compute baseline values from collected samples.
    
    Returns:
        True if baseline was successfully computed, False otherwise
    """
    global _baseline_computed, _baseline_hr, _baseline_eda, _baseline_hrv, _baseline_samples
    
    if len(_baseline_samples) < 10:  # Need at least 10 samples
        return False
    
    # Compute average values from baseline samples
    hr_values = [s['hr'] for s in _baseline_samples]
    eda_values = [s['eda'] for s in _baseline_samples]
    hrv_values = [s['hrv'] for s in _baseline_samples]
    
    _baseline_hr = sum(hr_values) / len(hr_values)
    _baseline_eda = sum(eda_values) / len(eda_values)
    _baseline_hrv = sum(hrv_values) / len(hrv_values)
    
    _baseline_computed = True
    return True

def get_baseline_status() -> dict:
    """Get current baseline protocol status."""
    global _current_time, _baseline_computed, _baseline_samples
    global _resting_period_seconds, _baseline_window_seconds
    
    status = {
        'current_time': _current_time,
        'resting_period_seconds': _resting_period_seconds,
        'baseline_window_seconds': _baseline_window_seconds,
        'in_resting_period': is_in_resting_period(),
        'in_baseline_window': is_in_baseline_window(),
        'baseline_computed': _baseline_computed,
        'baseline_samples_collected': len(_baseline_samples)
    }
    
    if _baseline_computed:
        status.update({
            'baseline_hr': _baseline_hr,
            'baseline_eda': _baseline_eda,
            'baseline_hrv': _baseline_hrv
        })
    
    return status

def reset_baseline_protocol() -> None:
    """Reset the baseline protocol to start over."""
    global _baseline_computed, _baseline_samples, _current_time
    global _baseline_hr, _baseline_eda, _baseline_hrv
    
    _baseline_computed = False
    _baseline_samples = []
    _current_time = 0
    
    # Reset to default baseline values
    _baseline_hr = 75.0
    _baseline_eda = 2.0
    _baseline_hrv = 50.0

def is_baseline_protocol_complete() -> bool:
    """Check if the baseline protocol is complete and active simulation can begin."""
    global _current_time, _resting_period_seconds, _baseline_window_seconds
    return _current_time >= (_resting_period_seconds + _baseline_window_seconds) and _baseline_computed
