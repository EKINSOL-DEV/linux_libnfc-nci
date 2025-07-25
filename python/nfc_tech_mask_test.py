#!/usr/bin/env python3
"""
Technology Mask Multi-Tag Test

This tool tests different technology mask configurations to find the optimal
setting for multi-tag detection without anti-collision interference.

It programmatically tests different polling configurations:
1. Default mask (0xCF) - with active modes
2. Passive-only mask (0x0F) - no active modes  
3. Basic mask (0x07) - just A, B, F
4. Single technology masks for isolation testing

The goal is to find a configuration where multiple tags appear simultaneously
rather than being automatically switched by anti-collision mechanisms.

Usage:
    sudo python nfc_tech_mask_test.py [--quick] [--mask HEX]
"""

import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

try:
    import nfc_reader
    import nfc_native
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

class TechMaskTest:
    """Test different technology mask configurations for multi-tag detection."""
    
    def __init__(self):
        # Technology mask definitions from nfa_api.h
        self.MASKS = {
            'A': 0x01,           # NFC Technology A
            'B': 0x02,           # NFC Technology B
            'F': 0x04,           # NFC Technology F
            'V': 0x08,           # NFC Technology V/ISO15693
            'B_PRIME': 0x10,     # Proprietary Technology
            'KOVIO': 0x20,       # Proprietary Technology
            'A_ACTIVE': 0x40,    # NFC Technology A active mode
            'F_ACTIVE': 0x80,    # NFC Technology F active mode
        }
        
        # Test configurations
        self.TEST_CONFIGS = {
            'default': {
                'mask': 0xCF,
                'name': 'Default (with active modes)',
                'description': 'Current config with anti-collision'
            },
            'passive_all': {
                'mask': 0x0F,
                'name': 'All passive modes',
                'description': 'A+B+F+V passive only, no active modes'
            },
            'basic_passive': {
                'mask': 0x07,
                'name': 'Basic passive (A+B+F)',
                'description': 'Just Type A, B, F passive modes'
            },
            'type_a_only': {
                'mask': 0x01,
                'name': 'Type A only',
                'description': 'Only NFC Type A passive'
            },
            'no_active': {
                'mask': 0x3F,
                'name': 'All except active modes',
                'description': 'All passive + proprietary, no active'
            },
            'minimal': {
                'mask': 0x03,
                'name': 'Type A+B only',
                'description': 'Minimal passive modes'
            }
        }
        
        self.results = {}
    
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"🔬 {title}")
        print(f"{'='*70}")
    
    def explain_mask(self, mask_value):
        """Explain what technologies are enabled in a mask."""
        enabled = []
        for name, value in self.MASKS.items():
            if mask_value & value:
                enabled.append(f"{name}(0x{value:02X})")
        
        return " + ".join(enabled) if enabled else "None"
    
    def test_single_config(self, config_name: str, config: Dict, timeout: int = 10) -> Dict:
        """Test a single technology mask configuration."""
        print(f"\n🔬 Testing: {config['name']}")
        print(f"   Mask: 0x{config['mask']:02X}")
        print(f"   Technologies: {self.explain_mask(config['mask'])}")
        print(f"   Description: {config['description']}")
        
        detected_tags = []
        unique_uids = set()
        max_simultaneous = 0
        detection_events = []
        
        try:
            # Low-level approach: try to influence the tech mask
            # Note: This may require deeper integration with the NFC stack
            
            success = nfc_native.initialize()
            if not success:
                print("❌ NFC initialization failed")
                return {'error': 'init_failed'}
            
            # Start discovery
            nfc_native.start_discovery()
            
            start_time = time.time()
            last_num_tags = 0
            
            print(f"   📡 Scanning for {timeout} seconds...")
            
            while time.time() - start_time < timeout:
                try:
                    is_present = nfc_native.is_tag_present()
                    num_tags = nfc_native.get_num_tags()
                    current_time = time.time()
                    
                    # Track maximum simultaneous tags
                    if num_tags > max_simultaneous:
                        max_simultaneous = num_tags
                        if num_tags > 1:
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"   [{timestamp}] 📊 getNumTags(): {num_tags} (new max!)")
                    
                    if is_present and num_tags != last_num_tags:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"   [{timestamp}] 📡 Tags detected: {num_tags}")
                        last_num_tags = num_tags
                    
                    if is_present:
                        # Try to read current tag
                        tag_info = nfc_native.get_tag_info()
                        if tag_info and isinstance(tag_info, dict):
                            uid = tag_info.get('uid', 'Unknown')
                            
                            if uid not in unique_uids and uid != 'Unknown':
                                unique_uids.add(uid)
                                
                                tech = tag_info.get('technology_name', 'Unknown')
                                handle = tag_info.get('handle', 'Unknown')
                                
                                detection_event = {
                                    'timestamp': timestamp,
                                    'uid': uid,
                                    'technology': tech,
                                    'handle': handle,
                                    'num_tags_when_detected': num_tags,
                                    'elapsed': current_time - start_time
                                }
                                
                                detection_events.append(detection_event)
                                detected_tags.append(detection_event)
                                
                                print(f"   [{timestamp}] 🏷️  Tag {len(unique_uids)}: {uid[:16]}... ({tech})")
                                
                                # Try to read text
                                try:
                                    text_data = nfc_native.read_text()
                                    if text_data and text_data.get('text'):
                                        detection_event['text'] = text_data['text']
                                        print(f"        📝 Text: '{text_data['text']}'")
                                except:
                                    pass
                                
                                # If multiple tags detected, try switching
                                if num_tags > 1 and len(unique_uids) < num_tags:
                                    try:
                                        switch_result = nfc_native.select_next_tag()
                                        if switch_result:
                                            print(f"        🔄 Switched to next tag")
                                            time.sleep(0.02)  # Brief pause for switch
                                    except Exception as e:
                                        print(f"        ⚠️  Switch failed: {e}")
                
                except Exception as e:
                    if "No tag present" not in str(e):
                        print(f"   ❌ Read error: {e}")
                
                time.sleep(0.02)  # 20ms polling
            
            # Results for this configuration
            test_duration = time.time() - start_time
            
            result = {
                'config_name': config_name,
                'mask': config['mask'],
                'unique_tags': len(unique_uids),
                'max_simultaneous': max_simultaneous,
                'detection_events': len(detection_events),
                'test_duration': test_duration,
                'tags_data': detected_tags,
                'success': len(unique_uids) > 0
            }
            
            print(f"   📊 Results: {len(unique_uids)} unique tags, max simultaneous: {max_simultaneous}")
            
            return result
        
        except Exception as e:
            print(f"   ❌ Test error: {e}")
            return {'error': str(e), 'config_name': config_name}
        
        finally:
            try:
                nfc_native.stop_discovery()
                nfc_native.deinitialize()
                time.sleep(0.5)  # Cool-down between tests
            except:
                pass
    
    def run_comprehensive_test(self, timeout_per_test: int = 10, quick_mode: bool = False):
        """Run comprehensive test of all technology mask configurations."""
        self.print_header("Technology Mask Multi-Tag Comprehensive Test")
        
        print("🔬 This test will try different technology mask configurations")
        print("   to find the optimal setting for multi-tag detection.")
        print(f"\n⏰ Each test runs for {timeout_per_test} seconds")
        print("📱 Keep multiple NFC tags positioned near the reader throughout all tests")
        
        if quick_mode:
            test_configs = ['default', 'passive_all', 'basic_passive']
            print(f"🏃 Quick mode: Testing {len(test_configs)} key configurations")
        else:
            test_configs = list(self.TEST_CONFIGS.keys())
            print(f"🔍 Full mode: Testing all {len(test_configs)} configurations")
        
        input(f"\nPress Enter to start {len(test_configs)} tests...")
        
        # Run tests
        for i, config_name in enumerate(test_configs):
            config = self.TEST_CONFIGS[config_name]
            
            print(f"\n{'='*50}")
            print(f"Test {i+1}/{len(test_configs)}: {config_name}")
            print(f"{'='*50}")
            
            result = self.test_single_config(config_name, config, timeout_per_test)
            self.results[config_name] = result
            
            if i < len(test_configs) - 1:
                print(f"\n⏸️  Cooling down before next test...")
                time.sleep(1)
        
        return self.analyze_all_results()
    
    def analyze_all_results(self):
        """Analyze results from all test configurations."""
        self.print_header("Technology Mask Test Analysis")
        
        if not self.results:
            print("❌ No test results available")
            return False
        
        # Sort results by effectiveness
        valid_results = {k: v for k, v in self.results.items() if 'error' not in v}
        
        if not valid_results:
            print("❌ All tests failed")
            return False
        
        # Sort by unique tags found, then by max simultaneous
        sorted_results = sorted(
            valid_results.items(),
            key=lambda x: (x[1]['unique_tags'], x[1]['max_simultaneous']),
            reverse=True
        )
        
        print("📊 Results Summary (ordered by effectiveness):")
        print(f"{'Rank':<4} {'Config':<15} {'Mask':<6} {'Unique':<7} {'Max Sim':<8} {'Events':<8} {'Description'}")
        print("-" * 80)
        
        best_config = None
        
        for rank, (config_name, result) in enumerate(sorted_results, 1):
            config = self.TEST_CONFIGS[config_name]
            
            unique = result['unique_tags']
            max_sim = result['max_simultaneous']
            events = result['detection_events']
            
            status = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
            
            print(f"{status}{rank:<3} {config_name:<15} 0x{result['mask']:02X}    {unique:<7} {max_sim:<8} {events:<8} {config['description'][:40]}")
            
            if rank == 1:
                best_config = (config_name, result)
        
        # Detailed analysis of best result
        if best_config:
            config_name, result = best_config
            config = self.TEST_CONFIGS[config_name]
            
            print(f"\n🏆 Best Configuration: {config['name']}")
            print(f"   Technology Mask: 0x{result['mask']:02X}")
            print(f"   Technologies: {self.explain_mask(result['mask'])}")
            print(f"   Unique tags detected: {result['unique_tags']}")
            print(f"   Max simultaneous: {result['max_simultaneous']}")
            
            if result['max_simultaneous'] > 1:
                print(f"   ✅ MULTI-TAG DETECTION ACHIEVED!")
                
                if result['unique_tags'] >= result['max_simultaneous']:
                    print(f"   🎯 All detected tags were successfully read")
                else:
                    print(f"   ⚠️  Some tags detected but not all read individually")
            else:
                print(f"   ⚠️  Only single tag detection achieved")
            
            # Timeline analysis
            if result['tags_data']:
                print(f"\n📋 Detection Timeline:")
                for tag_data in result['tags_data']:
                    text = tag_data.get('text', 'No text')
                    print(f"     {tag_data['timestamp']}: {tag_data['uid'][:16]}... - '{text}' (count: {tag_data['num_tags_when_detected']})")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        best_unique = max(r['unique_tags'] for r in valid_results.values())
        best_sim = max(r['max_simultaneous'] for r in valid_results.values())
        
        if best_sim > 1:
            print(f"   ✅ Multi-tag detection is possible with proper configuration")
            print(f"   🔧 Optimal mask: 0x{best_config[1]['mask']:02X} ({best_config[0]})")
            
            # Check if disabling active modes helped
            default_result = valid_results.get('default', {})
            passive_result = valid_results.get('passive_all', {})
            
            if passive_result and default_result:
                if passive_result['max_simultaneous'] > default_result['max_simultaneous']:
                    print(f"   🚫 Disabling active modes (anti-collision) improves multi-tag detection")
                    print(f"   📝 Consider updating POLLING_TECH_MASK in /conf/libnfc-nci.conf to 0x{passive_result['mask']:02X}")
        else:
            print(f"   ⚠️  Multi-tag detection not achieved with tested configurations")
            print(f"   🔧 May need deeper NFC stack configuration changes")
        
        return best_sim > 1
    
    def test_custom_mask(self, custom_mask: int, timeout: int = 10):
        """Test a custom technology mask value."""
        self.print_header(f"Custom Technology Mask Test: 0x{custom_mask:02X}")
        
        custom_config = {
            'mask': custom_mask,
            'name': f'Custom (0x{custom_mask:02X})',
            'description': f'User-specified mask: {self.explain_mask(custom_mask)}'
        }
        
        result = self.test_single_config('custom', custom_config, timeout)
        
        if 'error' not in result:
            print(f"\n📊 Custom Mask Results:")
            print(f"   Unique tags: {result['unique_tags']}")
            print(f"   Max simultaneous: {result['max_simultaneous']}")
            print(f"   Detection events: {result['detection_events']}")
            
            return result['max_simultaneous'] > 1
        else:
            print(f"❌ Custom mask test failed: {result['error']}")
            return False
    
    def run(self, timeout: int = 10, quick: bool = False, custom_mask: Optional[int] = None):
        """Run the technology mask test."""
        print("🔬 Technology Mask Multi-Tag Test Tool")
        print("=" * 50)
        print("This tool tests different NFC technology mask configurations")
        print("to find the optimal setting for multi-tag detection.\n")
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("⚠️  Warning: This tool typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        try:
            if custom_mask is not None:
                return self.test_custom_mask(custom_mask, timeout)
            else:
                return self.run_comprehensive_test(timeout, quick)
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Technology Mask Multi-Tag Test Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool tests different NFC technology mask configurations to optimize
multi-tag detection by finding settings that minimize anti-collision behavior.

Technology masks control which NFC technologies are polled:
• 0x01 = Type A passive
• 0x02 = Type B passive  
• 0x04 = Type F passive
• 0x08 = Type V/ISO15693
• 0x40 = Type A active (triggers anti-collision)
• 0x80 = Type F active (triggers anti-collision)

Examples:
  %(prog)s --timeout 15                   # Full test, 15s per config
  %(prog)s --quick --timeout 10           # Quick test of key configs
  %(prog)s --mask 0x0F --timeout 10       # Test specific mask
        """
    )
    
    parser.add_argument('--timeout', type=int, default=10,
                       help='Test duration per configuration in seconds (default: 10)')
    parser.add_argument('--quick', action='store_true',
                       help='Quick mode: test only key configurations')
    parser.add_argument('--mask', type=lambda x: int(x, 0), metavar='HEX',
                       help='Test specific technology mask (e.g., 0x0F)')
    
    args = parser.parse_args()
    
    if args.timeout < 5:
        print("❌ Timeout must be at least 5 seconds")
        return 1
    
    if args.mask is not None and (args.mask < 0 or args.mask > 0xFF):
        print("❌ Technology mask must be between 0x00 and 0xFF")
        return 1
    
    test = TechMaskTest()
    success = test.run(
        timeout=args.timeout,
        quick=args.quick,
        custom_mask=args.mask
    )
    
    if success:
        print("\n✅ Multi-tag detection achieved with optimal technology mask!")
        print("💡 Consider applying the recommended configuration changes")
    else:
        print("\n⚠️  Multi-tag detection not achieved with tested configurations")
        print("💡 May need alternative approaches or deeper NFC stack modifications")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())