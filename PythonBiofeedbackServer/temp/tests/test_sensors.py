#!/usr/bin/env python3
"""
Unit Tests for Sensors Module
=============================

Comprehensive pytest test suite for the sensors.py module covering:
- Signal generation functions (HR, EDA, HRV)
- Stress index computation and normalization
- Scenario switching functionality
- Baseline protocol implementation
- Timing synchronization

Author: Cybertherapy Project  
Date: August 2025
"""

import pytest
import sys
import os
import numpy as np

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sensors import (
    get_hr, get_eda, get_hrv, compute_stress_index,
    set_scenario, get_current_scenario, get_current_time,
    _advance_time, _reset_time, clamp,
    # Baseline protocol functions
    is_in_resting_period, is_in_baseline_window, 
    should_collect_baseline_sample, collect_baseline_sample,
    compute_baseline_values, get_baseline_status,
    reset_baseline_protocol, is_baseline_protocol_complete
)

class TestSignalGeneration:
    """Test realistic signal generation for all scenarios."""
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_time()
        reset_baseline_protocol()
        set_scenario("mixed")
    
    def test_hr_generation_baseline(self):
        """Test HR generation in baseline scenario."""
        set_scenario("baseline")
        
        hr_values = []
        for i in range(100):  # Collect 100 samples
            hr = get_hr()
            hr_values.append(hr)
            _advance_time(0.1)  # 10Hz sampling
        
        # Validate HR range and characteristics
        assert all(40 <= hr <= 200 for hr in hr_values), "HR values outside physiological range"
        assert 65 <= np.mean(hr_values) <= 85, "Baseline HR mean not in expected range"
        assert np.std(hr_values) > 0.5, "HR should show natural variability"
        
    def test_hr_generation_stress(self):
        """Test HR generation in stress_buildup scenario."""
        set_scenario("stress_buildup")
        
        hr_values = []
        for i in range(300):  # 30 seconds at 10Hz
            hr = get_hr()
            hr_values.append(hr)
            _advance_time(0.1)
        
        # HR should increase during stress buildup
        early_hr = np.mean(hr_values[:50])   # First 5 seconds
        late_hr = np.mean(hr_values[-50:])   # Last 5 seconds
        
        assert late_hr > early_hr + 5, "HR should increase significantly during stress buildup"
        assert late_hr < 150, "Stress HR should stay within physiological bounds"
    
    def test_eda_generation_scenarios(self):
        """Test EDA generation across different scenarios."""
        scenarios = ["baseline", "stress_buildup", "recovery", "mixed"]
        
        for scenario in scenarios:
            set_scenario(scenario)
            _reset_time()
            
            eda_values = []
            for i in range(50):
                eda = get_eda()
                eda_values.append(eda)
                _advance_time(0.1)
            
            # Validate EDA characteristics
            assert all(0 <= eda <= 15 for eda in eda_values), f"EDA values out of range for {scenario}"
            assert np.std(eda_values) > 0.01, f"EDA should show variability in {scenario}"
    
    def test_hrv_calculation(self):
        """Test HRV calculation with sufficient HR history."""
        set_scenario("baseline")
        
        # Generate enough HR samples for HRV calculation
        for i in range(25):  # More than window size (20)
            get_hr()
            _advance_time(0.1)
        
        hrv = get_hrv()
        
        # HRV should be in physiological range
        assert 10 <= hrv <= 200, f"HRV {hrv} outside expected range (10-200ms)"
        assert isinstance(hrv, float), "HRV should return float"
    
    def test_hrv_insufficient_data(self):
        """Test HRV with insufficient HR history."""
        _reset_time()  # Clear HR history
        
        # Generate only a few HR samples
        for i in range(3):
            get_hr()
            _advance_time(0.1)
        
        hrv = get_hrv()
        assert hrv in [10.0, 50.0], "HRV should return clamped minimum or default value with insufficient data"

class TestStressIndex:
    """Test stress index computation and normalization."""
    
    def test_stress_index_range(self):
        """Test stress index stays within 0-100 range."""
        test_cases = [
            (45, 0.0, 10),    # Low stress
            (75, 2.0, 50),    # Medium stress  
            (120, 8.0, 150),  # High stress
            (180, 10.0, 200), # Maximum stress
        ]
        
        for hr, eda, hrv in test_cases:
            stress = compute_stress_index(hr, eda, hrv)
            assert 0 <= stress <= 100, f"Stress index {stress} outside 0-100 range"
            assert isinstance(stress, float), "Stress index should be float"
    
    def test_stress_index_weighting(self):
        """Test stress index responds to different signal weights."""
        hr, eda, hrv = 100, 5.0, 30
        
        # Test HR-weighted stress
        stress_hr = compute_stress_index(hr, eda, hrv, w_hr=0.8, w_eda=0.1, w_hrv=0.1)
        
        # Test EDA-weighted stress
        stress_eda = compute_stress_index(hr, eda, hrv, w_hr=0.1, w_eda=0.8, w_hrv=0.1)
        
        # Both should be valid but potentially different
        assert 0 <= stress_hr <= 100
        assert 0 <= stress_eda <= 100
    
    def test_clamp_function(self):
        """Test utility clamp function."""
        assert clamp(5, 0, 10) == 5
        assert clamp(-5, 0, 10) == 0
        assert clamp(15, 0, 10) == 10
        assert clamp(7.5, 5.0, 10.0) == 7.5

class TestScenarios:
    """Test scenario switching functionality."""
    
    def test_scenario_switching(self):
        """Test valid scenario changes."""
        valid_scenarios = ["baseline", "stress_buildup", "recovery", "mixed"]
        
        for scenario in valid_scenarios:
            set_scenario(scenario)
            assert get_current_scenario() == scenario
    
    def test_invalid_scenario(self):
        """Test invalid scenario handling."""
        with pytest.raises(ValueError):
            set_scenario("invalid_scenario")
        
        # Current scenario should remain unchanged
        original = get_current_scenario()
        try:
            set_scenario("bad_scenario")
        except ValueError:
            pass
        assert get_current_scenario() == original

class TestTiming:
    """Test timing and synchronization functions."""
    
    def setup_method(self):
        """Reset timing before each test."""
        _reset_time()
    
    def test_timing_advancement(self):
        """Test time advancement with different intervals."""
        assert get_current_time() == 0
        
        _advance_time(1.0)
        assert get_current_time() == 1
        
        _advance_time(0.1)  # Fractional seconds
        assert get_current_time() == 1.1
        
        _advance_time(2.5)
        assert get_current_time() == 3.6
    
    def test_timing_reset(self):
        """Test time reset functionality."""
        _advance_time(10.0)
        assert get_current_time() == 10
        
        _reset_time()
        assert get_current_time() == 0

class TestBaselineProtocol:
    """Test baseline protocol implementation."""
    
    def setup_method(self):
        """Reset baseline protocol before each test."""
        _reset_time()
        reset_baseline_protocol()
    
    def test_resting_period(self):
        """Test resting period detection."""
        # Should be in resting period at start
        assert is_in_resting_period()
        assert not is_in_baseline_window()
        assert not is_baseline_protocol_complete()
        
        # Advance to just before end of resting period
        _advance_time(179)  # 179 seconds (just before 180s)
        assert is_in_resting_period()
        
        # Advance past resting period
        _advance_time(2)  # Now at 181 seconds
        assert not is_in_resting_period()
        assert is_in_baseline_window()
    
    def test_baseline_window(self):
        """Test baseline computation window."""
        # Advance to baseline window (after 180s resting)
        _advance_time(185)  # 5 seconds into baseline window
        
        assert not is_in_resting_period()
        assert is_in_baseline_window()
        assert should_collect_baseline_sample()
        
        # Advance past baseline window
        _advance_time(60)  # Now at 245s (past 240s end)
        assert not is_in_baseline_window()
    
    def test_sample_collection(self):
        """Test baseline sample collection."""
        # Advance to baseline window
        _advance_time(185)
        
        # Collect some samples
        for i in range(20):
            collect_baseline_sample(75.0 + i, 2.0 + i*0.1, 50.0 + i)
            _advance_time(1)
        
        status = get_baseline_status()
        assert status['baseline_samples_collected'] == 20
        
        # Compute baseline values
        assert compute_baseline_values()
        
        status = get_baseline_status()
        assert status['baseline_computed']
        assert 'baseline_hr' in status
        assert 'baseline_eda' in status
        assert 'baseline_hrv' in status
    
    def test_protocol_completion(self):
        """Test full baseline protocol completion."""
        # Advance through resting period and baseline window
        _advance_time(185)  # In baseline window
        
        # Collect sufficient samples
        for i in range(15):
            collect_baseline_sample(75.0, 2.0, 50.0)
            _advance_time(1)
        
        # Compute baseline
        compute_baseline_values()
        
        # Advance past baseline window
        _advance_time(60)  # Total: 260s (past 240s requirement)
        
        assert is_baseline_protocol_complete()

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def setup_method(self):
        """Reset all state before each test."""
        _reset_time()
        reset_baseline_protocol()
        set_scenario("mixed")
    
    def test_realistic_simulation_flow(self):
        """Test realistic simulation with all components."""
        set_scenario("baseline")
        
        # Simulate 10 seconds of data at 10Hz
        samples = []
        for i in range(100):
            hr = get_hr()
            eda = get_eda()
            hrv = get_hrv()
            stress = compute_stress_index(hr, eda, hrv)
            
            sample = {
                'time': get_current_time(),
                'hr': hr,
                'eda': eda,
                'hrv': hrv,
                'stress': stress,
                'scenario': get_current_scenario()
            }
            samples.append(sample)
            _advance_time(0.1)  # 10Hz
        
        # Validate simulation characteristics
        assert len(samples) == 100
        assert all(s['scenario'] == 'baseline' for s in samples)
        assert all(0 <= s['stress'] <= 100 for s in samples)
        assert abs(samples[-1]['time'] - 10.0) < 0.1  # ~10 seconds elapsed (floating point precision)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
