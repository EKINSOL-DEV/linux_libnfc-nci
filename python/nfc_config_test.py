#!/usr/bin/env python3
"""
NFC Configuration Test Tool

This tool tests multi-tag detection by temporarily modifying the NFC configuration
to disable anti-collision mechanisms. It safely backs up and restores the original
configuration.

It tests changing POLLING_TECH_MASK from 0xCF (with active modes) to 0x0F 
(passive only) to see if this eliminates anti-collision behavior and allows
true simultaneous multi-tag detection.

Usage:
    sudo python nfc_config_test.py [--timeout T] [--mask HEX]
"""

import sys
import time
import argparse
import shutil
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import nfc_reader
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

class ConfigTest:
    """Test multi-tag detection with temporary configuration changes."""
    
    def __init__(self):
        self.config_path = "/Users/ekinsol_nicky/Documents/GitHub/linux_libnfc-nci/conf/libnfc-nci.conf"
        self.backup_path = self.config_path + ".backup"
        self.original_mask = None
        self.test_results = {}
    
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"⚙️  {title}")
        print(f"{'='*70}")
    
    def backup_config(self):
        """Create backup of original configuration."""
        try:
            if os.path.exists(self.config_path):
                shutil.copy2(self.config_path, self.backup_path)
                print(f"✅ Configuration backed up to {self.backup_path}")
                return True
            else:
                print(f"❌ Configuration file not found: {self.config_path}")
                return False
        except Exception as e:
            print(f"❌ Failed to backup configuration: {e}")
            return False
    
    def restore_config(self):
        """Restore original configuration from backup."""
        try:
            if os.path.exists(self.backup_path):
                shutil.copy2(self.backup_path, self.config_path)
                os.remove(self.backup_path)
                print(f"✅ Original configuration restored")
                return True
            else:
                print(f"⚠️  No backup found at {self.backup_path}")
                return False
        except Exception as e:
            print(f"❌ Failed to restore configuration: {e}")
            return False
    
    def read_current_mask(self):
        """Read current POLLING_TECH_MASK from configuration."""
        try:
            with open(self.config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('POLLING_TECH_MASK='):
                        value_str = line.split('=')[1].strip()
                        if value_str.startswith('0x'):
                            return int(value_str, 16)
                        else:
                            return int(value_str)
            return None
        except Exception as e:
            print(f"❌ Failed to read configuration: {e}")
            return None
    
    def update_tech_mask(self, new_mask):
        """Update POLLING_TECH_MASK in configuration file."""
        try:
            # Read current config
            with open(self.config_path, 'r') as f:
                lines = f.readlines()
            
            # Update the mask line
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith('POLLING_TECH_MASK='):
                    lines[i] = f"POLLING_TECH_MASK=0x{new_mask:02X}\n"
                    updated = True
                    break
            
            if not updated:
                print(f"⚠️  POLLING_TECH_MASK not found in config, appending...")
                lines.append(f"POLLING_TECH_MASK=0x{new_mask:02X}\n")
            
            # Write updated config
            with open(self.config_path, 'w') as f:
                f.writelines(lines)
            
            print(f"✅ Updated POLLING_TECH_MASK to 0x{new_mask:02X}")
            return True
        
        except Exception as e:
            print(f"❌ Failed to update configuration: {e}")
            return False
    
    def test_with_mask(self, mask_value, mask_name, timeout=15):
        """Test multi-tag detection with a specific technology mask."""
        print(f"\n🔬 Testing with {mask_name} (0x{mask_value:02X})")
        
        detected_tags = []
        unique_uids = set()
        max_simultaneous = 0
        detection_events = []
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                start_time = time.time()
                last_num_tags = 0
                
                print(f"   📡 Scanning for {timeout} seconds...")
                
                while time.time() - start_time < timeout:
                    is_present = reader.is_tag_present()
                    num_tags = reader.get_num_tags()
                    current_time = time.time()
                    
                    # Track maximum simultaneous
                    if num_tags > max_simultaneous:
                        max_simultaneous = num_tags
                        if num_tags > 1:
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"   [{timestamp}] 📊 getNumTags(): {num_tags} (new max!)")
                    
                    if is_present and num_tags != last_num_tags:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"   [{timestamp}] 📡 Tags present: {num_tags}")
                        last_num_tags = num_tags
                    
                    if is_present:
                        tag_info = reader.get_tag_info()
                        if tag_info and isinstance(tag_info, dict):
                            uid = tag_info.get('uid', 'Unknown')
                            
                            if uid not in unique_uids and uid != 'Unknown':
                                unique_uids.add(uid)
                                
                                tech = tag_info.get('technology_name', 'Unknown')
                                
                                detection_event = {
                                    'timestamp': timestamp,
                                    'uid': uid,
                                    'technology': tech,
                                    'num_tags_when_detected': num_tags,
                                    'elapsed': current_time - start_time,
                                    'mask_used': mask_value
                                }
                                
                                detection_events.append(detection_event)
                                detected_tags.append(detection_event)
                                
                                print(f"   [{timestamp}] 🏷️  Tag {len(unique_uids)}: {uid[:16]}... ({tech})")
                                
                                # Try to read text
                                try:
                                    text_data = reader.read_text()
                                    if text_data and text_data.get('text'):
                                        detection_event['text'] = text_data['text']
                                        print(f"        📝 Text: '{text_data['text']}'")
                                except:
                                    pass
                    
                    time.sleep(0.02)  # 20ms polling
                
                # Compile results
                result = {
                    'mask_value': mask_value,
                    'mask_name': mask_name,
                    'unique_tags': len(unique_uids),
                    'max_simultaneous': max_simultaneous,
                    'detection_events': len(detection_events),
                    'test_duration': time.time() - start_time,
                    'tags_data': detected_tags,
                    'success': len(unique_uids) > 0
                }
                
                print(f"   📊 Results: {len(unique_uids)} unique, max simultaneous: {max_simultaneous}")
                
                return result
        
        except Exception as e:
            print(f"   ❌ Test error: {e}")
            return {'error': str(e), 'mask_value': mask_value, 'mask_name': mask_name}
    
    def run_comparison_test(self, test_mask=0x0F, timeout=15):
        """Run comparison test between original and modified configuration."""
        self.print_header("Configuration-Based Multi-Tag Test")
        
        print("⚙️  This test compares multi-tag detection between:")
        print("   1. Original configuration (with anti-collision)")
        print("   2. Modified configuration (anti-collision disabled)")
        print(f"\n📱 Place multiple NFC tags near the reader for both tests")
        print(f"⏰ Each test runs for {timeout} seconds")
        
        # Check permissions
        if os.geteuid() != 0:
            print("\n⚠️  Warning: This test requires root privileges to modify config files.")
            print("Please run with 'sudo'")
            return False
        
        # Backup original configuration
        if not self.backup_config():
            return False
        
        # Read original mask
        self.original_mask = self.read_current_mask()
        if self.original_mask is None:
            print("❌ Could not read original POLLING_TECH_MASK")
            return False
        
        print(f"📋 Original POLLING_TECH_MASK: 0x{self.original_mask:02X}")
        print(f"📋 Test POLLING_TECH_MASK: 0x{test_mask:02X}")
        
        try:
            # Test 1: Original configuration
            input(f"\nPress Enter to start Test 1 (original configuration)...")
            
            original_result = self.test_with_mask(self.original_mask, "Original config", timeout)
            self.test_results['original'] = original_result
            
            # Test 2: Modified configuration
            print(f"\n🔄 Updating configuration for Test 2...")
            if not self.update_tech_mask(test_mask):
                return False
            
            print(f"⏸️  Waiting 2 seconds for config to take effect...")
            time.sleep(2)
            
            input(f"Press Enter to start Test 2 (modified configuration)...")
            
            modified_result = self.test_with_mask(test_mask, "Modified config", timeout)
            self.test_results['modified'] = modified_result
            
            # Analysis
            return self.analyze_comparison_results()
        
        finally:
            # Always restore original configuration
            print(f"\n🔄 Restoring original configuration...")
            self.restore_config()
    
    def analyze_comparison_results(self):
        """Analyze and compare test results."""
        self.print_header("Configuration Test Analysis")
        
        original = self.test_results.get('original', {})
        modified = self.test_results.get('modified', {})
        
        if 'error' in original or 'error' in modified:
            print("❌ One or both tests failed")
            return False
        
        print("📊 Comparison Results:")
        print(f"{'Metric':<25} {'Original':<15} {'Modified':<15} {'Change'}")
        print("-" * 70)
        
        orig_unique = original['unique_tags']
        mod_unique = modified['unique_tags']
        unique_change = mod_unique - orig_unique
        unique_symbol = "✅" if unique_change > 0 else "🔄" if unique_change == 0 else "⚠️"
        
        orig_max = original['max_simultaneous']
        mod_max = modified['max_simultaneous']
        max_change = mod_max - orig_max
        max_symbol = "✅" if max_change > 0 else "🔄" if max_change == 0 else "⚠️"
        
        orig_events = original['detection_events']
        mod_events = modified['detection_events']
        
        print(f"{'Unique tags detected':<25} {orig_unique:<15} {mod_unique:<15} {unique_symbol} {unique_change:+d}")
        print(f"{'Max simultaneous':<25} {orig_max:<15} {mod_max:<15} {max_symbol} {max_change:+d}")
        print(f"{'Detection events':<25} {orig_events:<15} {mod_events:<15}")
        print(f"{'Tech mask used':<25} 0x{original['mask_value']:02X}          0x{modified['mask_value']:02X}")
        
        # Detailed analysis
        improvement_found = False
        
        if mod_unique > orig_unique:
            print(f"\n✅ IMPROVEMENT: Modified config detected {unique_change} more unique tags!")
            improvement_found = True
        
        if mod_max > orig_max:
            print(f"✅ IMPROVEMENT: Modified config achieved {max_change} higher simultaneous detection!")
            improvement_found = True
        
        if mod_max > 1 and orig_max <= 1:
            print(f"🎯 BREAKTHROUGH: Modified config achieved multi-tag detection!")
            improvement_found = True
        
        if not improvement_found:
            if mod_unique == orig_unique and mod_max == orig_max:
                print(f"\n🔄 NO CHANGE: Both configurations performed similarly")
                print(f"   May need different approach or deeper configuration changes")
            else:
                print(f"\n⚠️  REGRESSION: Modified configuration performed worse")
                print(f"   Original anti-collision behavior may be beneficial")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if improvement_found:
            print(f"   ✅ Configuration change is beneficial for multi-tag detection")
            print(f"   🔧 Consider permanently setting POLLING_TECH_MASK=0x{modified['mask_value']:02X}")
            print(f"   📝 Update /conf/libnfc-nci.conf with the improved setting")
        else:
            print(f"   🔄 Keep original configuration (POLLING_TECH_MASK=0x{original['mask_value']:02X})")
            print(f"   🔧 Try alternative approaches like discovery event capture modification")
        
        # Show detection timelines if available
        if modified['tags_data']:
            print(f"\n📋 Modified Config Detection Timeline:")
            for tag_data in modified['tags_data']:
                text = tag_data.get('text', 'No text')
                print(f"     {tag_data['timestamp']}: {tag_data['uid'][:16]}... - '{text}' (count: {tag_data['num_tags_when_detected']})")
        
        return improvement_found
    
    def run(self, timeout: int = 15, test_mask: int = 0x0F):
        """Run the configuration test."""
        print("⚙️  NFC Configuration Multi-Tag Test Tool")
        print("=" * 50)
        print("This tool tests multi-tag detection by temporarily modifying")
        print("the NFC configuration to disable anti-collision mechanisms.\n")
        
        print(f"🔧 Test approach:")
        print(f"   1. Backup current configuration")
        print(f"   2. Test with original POLLING_TECH_MASK")
        print(f"   3. Test with modified POLLING_TECH_MASK (0x{test_mask:02X})")
        print(f"   4. Compare results and restore original config")
        
        try:
            return self.run_comparison_test(test_mask, timeout)
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="NFC Configuration Multi-Tag Test Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool tests multi-tag detection by temporarily modifying the NFC 
configuration file to disable anti-collision mechanisms.

The test:
1. Backs up current configuration
2. Tests with original POLLING_TECH_MASK (usually 0xCF)
3. Tests with modified POLLING_TECH_MASK (default 0x0F - passive only)
4. Compares results and restores original configuration

WARNING: Requires root privileges to modify configuration files.

Examples:
  %(prog)s --timeout 20                   # Standard test
  %(prog)s --mask 0x07 --timeout 15       # Test with basic passive modes
        """
    )
    
    parser.add_argument('--timeout', type=int, default=15,
                       help='Test duration per configuration in seconds (default: 15)')
    parser.add_argument('--mask', type=lambda x: int(x, 0), default=0x0F, metavar='HEX',
                       help='Technology mask to test (default: 0x0F - passive only)')
    
    args = parser.parse_args()
    
    if args.timeout < 5:
        print("❌ Timeout must be at least 5 seconds")
        return 1
    
    if args.mask < 0 or args.mask > 0xFF:
        print("❌ Technology mask must be between 0x00 and 0xFF")
        return 1
    
    test = ConfigTest()
    success = test.run(timeout=args.timeout, test_mask=args.mask)
    
    if success:
        print("\n✅ Configuration change improved multi-tag detection!")
        print("💡 Consider making the change permanent in libnfc-nci.conf")
    else:
        print("\n⚠️  Configuration change did not improve multi-tag detection")
        print("💡 Original configuration may be optimal, or alternative approaches needed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())