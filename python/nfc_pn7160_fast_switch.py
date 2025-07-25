#!/usr/bin/env python3
"""
PN7160 Fast Tag Switching Performance Tool

This tool optimizes the PN7160's sequential tag switching performance
by minimizing polling intervals and maximizing tag switching speed.

Based on the discovery mechanism analysis:
- PN7160 supports anti-collision during RF_DISCOVER_NTF phase
- Multiple tags are detected sequentially, not simultaneously  
- selectNextTag() and checkNextProtocol() enable tag switching
- Performance is limited by polling intervals and discovery cycles

This tool tests and optimizes switching performance for scenarios where
you need to rapidly cycle through multiple tags (e.g., inventory systems).

Usage:
    sudo python nfc_pn7160_fast_switch.py [--min-tags N] [--cycles C]
"""

import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import nfc_reader
    import nfc_native
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

class PN7160FastSwitch:
    """Performance-optimized PN7160 multi-tag switching."""
    
    def __init__(self):
        self.switching_metrics = []
        self.detected_tags = []
        self.performance_data = {
            'switch_times': [],
            'read_times': [],
            'detection_times': [],
            'cycle_times': []
        }
    
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"⚡ {title}")
        print(f"{'='*70}")
    
    def fast_discovery_scan(self, min_tags=2, timeout=15):
        """
        Fast discovery scan to identify all available tags quickly.
        Optimized for speed with minimal polling intervals.
        """
        self.print_header("Fast Discovery Scan")
        
        print("⚡ Optimized discovery scan for PN7160 anti-collision")
        print(f"📱 Place {min_tags}+ NFC tags near the reader")
        print("   Keep them positioned during the entire scan")
        print(f"⏰ Fast scan timeout: {timeout} seconds")
        
        input("\nPress Enter to start fast discovery scan...")
        
        discovered_uids = set()
        discovery_events = []
        
        try:
            success = nfc_native.initialize()
            if not success:
                print("❌ NFC initialization failed")
                return []
            
            nfc_native.start_discovery()
            
            start_time = time.time()
            scan_start = start_time
            
            print(f"\n🔍 Fast scanning... (interval: 20ms)")
            
            while time.time() - start_time < timeout:
                try:
                    discovery_start = time.time()
                    
                    is_present = nfc_native.is_tag_present()
                    if is_present:
                        # Fast tag info retrieval
                        tag_info = nfc_native.get_tag_info()
                        if tag_info and isinstance(tag_info, dict):
                            uid = tag_info.get('uid', 'Unknown')
                            
                            if uid not in discovered_uids and uid != 'Unknown':
                                discovered_uids.add(uid)
                                
                                discovery_time = time.time() - discovery_start
                                
                                tag_data = {
                                    'uid': uid,
                                    'technology': tag_info.get('technology_name', 'Unknown'),
                                    'handle': tag_info.get('handle', 'Unknown'),
                                    'discovery_time': discovery_time,
                                    'scan_elapsed': time.time() - scan_start
                                }
                                
                                self.detected_tags.append(tag_data)
                                self.performance_data['detection_times'].append(discovery_time)
                                
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                print(f"[{timestamp}] ⚡ Tag {len(discovered_uids)}: {uid[:16]}... "
                                      f"({tag_info.get('technology_name', 'Unknown')}) "
                                      f"- {discovery_time*1000:.1f}ms")
                                
                                # Quick text read attempt (optional)
                                try:
                                    text_start = time.time()
                                    text_data = nfc_native.read_text()
                                    read_time = time.time() - text_start
                                    
                                    if text_data and text_data.get('text'):
                                        tag_data['text'] = text_data['text']
                                        self.performance_data['read_times'].append(read_time)
                                        print(f"    📝 Text: '{text_data['text']}' - {read_time*1000:.1f}ms")
                                except:
                                    pass
                    
                    # Minimal polling interval for maximum speed
                    time.sleep(0.02)  # 20ms intervals
                    
                except Exception as e:
                    print(f"❌ Discovery error: {e}")
                    time.sleep(0.05)
            
            scan_duration = time.time() - scan_start
            
            print(f"\n📊 Fast Discovery Results:")
            print(f"   Scan duration: {scan_duration:.1f}s")
            print(f"   Tags discovered: {len(discovered_uids)}")
            
            if self.performance_data['detection_times']:
                avg_detection = sum(self.performance_data['detection_times']) / len(self.performance_data['detection_times']) * 1000
                min_detection = min(self.performance_data['detection_times']) * 1000
                max_detection = max(self.performance_data['detection_times']) * 1000
                print(f"   Detection time: {avg_detection:.1f}ms avg ({min_detection:.1f}-{max_detection:.1f}ms)")
            
            if self.performance_data['read_times']:
                avg_read = sum(self.performance_data['read_times']) / len(self.performance_data['read_times']) * 1000
                print(f"   Text read time: {avg_read:.1f}ms avg")
            
            return self.detected_tags
            
        except Exception as e:
            print(f"❌ Fast discovery error: {e}")
            return []
        
        finally:
            try:
                nfc_native.stop_discovery()
                nfc_native.deinitialize()
            except:
                pass
    
    def performance_switching_test(self, target_cycles=10, timeout=30):
        """
        Performance test for rapid tag switching using selectNextTag().
        Measures switching speed and reliability.
        """
        self.print_header("Performance Switching Test")
        
        if len(self.detected_tags) < 2:
            print("❌ Need at least 2 detected tags for switching test")
            return False
        
        print(f"⚡ Testing rapid tag switching performance")
        print(f"🎯 Target: {target_cycles} switching cycles")
        print(f"📱 Using {len(self.detected_tags)} detected tags")
        print(f"⏰ Max duration: {timeout} seconds")
        
        input("\nPress Enter to start performance switching test...")
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                start_time = time.time()
                cycle_count = 0
                successful_switches = 0
                switch_failures = 0
                
                print(f"\n⚡ Fast switching test... (target interval: 100ms)")
                
                while cycle_count < target_cycles and time.time() - start_time < timeout:
                    cycle_start = time.time()
                    
                    try:
                        if reader.is_tag_present():
                            num_tags = reader.get_num_tags()
                            
                            # Get current tag
                            current_info = reader.get_tag_info()
                            if current_info:
                                current_uid = current_info.get('uid', 'Unknown')
                                
                                # Attempt fast switch
                                switch_start = time.time()
                                switch_result = nfc_native.select_next_tag()
                                switch_time = time.time() - switch_start
                                
                                if switch_result:
                                    # Verify switch by checking new tag
                                    new_info = reader.get_tag_info()
                                    if new_info:
                                        new_uid = new_info.get('uid', 'Unknown')
                                        
                                        if new_uid != current_uid:
                                            successful_switches += 1
                                            self.performance_data['switch_times'].append(switch_time)
                                            
                                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                            print(f"[{timestamp}] ✅ Switch {successful_switches}: "
                                                  f"{current_uid[:12]}→{new_uid[:12]} "
                                                  f"({switch_time*1000:.1f}ms)")
                                        else:
                                            switch_failures += 1
                                            print(f"    🔄 Same tag after switch (cycle {cycle_count+1})")
                                    else:
                                        switch_failures += 1
                                        print(f"    ❌ No tag info after switch")
                                else:
                                    switch_failures += 1
                                    print(f"    ❌ selectNextTag() failed")
                    
                    except Exception as e:
                        switch_failures += 1
                        print(f"    ❌ Switch cycle error: {e}")
                    
                    cycle_time = time.time() - cycle_start
                    self.performance_data['cycle_times'].append(cycle_time)
                    cycle_count += 1
                    
                    # Performance-optimized interval
                    time.sleep(0.1)  # 100ms between switch attempts
                
                # Performance analysis
                test_duration = time.time() - start_time
                
                print(f"\n📊 Performance Switching Results:")
                print(f"   Test duration: {test_duration:.1f}s")
                print(f"   Cycles completed: {cycle_count}")
                print(f"   Successful switches: {successful_switches}")
                print(f"   Switch failures: {switch_failures}")
                print(f"   Success rate: {successful_switches/(successful_switches+switch_failures)*100:.1f}%" if (successful_switches+switch_failures) > 0 else "0%")
                
                if self.performance_data['switch_times']:
                    switch_times_ms = [t * 1000 for t in self.performance_data['switch_times']]
                    avg_switch = sum(switch_times_ms) / len(switch_times_ms)
                    min_switch = min(switch_times_ms)
                    max_switch = max(switch_times_ms)
                    print(f"   Switch time: {avg_switch:.1f}ms avg ({min_switch:.1f}-{max_switch:.1f}ms)")
                
                if self.performance_data['cycle_times']:
                    cycle_times_ms = [t * 1000 for t in self.performance_data['cycle_times']]
                    avg_cycle = sum(cycle_times_ms) / len(cycle_times_ms)
                    print(f"   Cycle time: {avg_cycle:.1f}ms avg")
                    print(f"   Theoretical max rate: {1000/avg_cycle:.1f} switches/second")
                
                return successful_switches >= target_cycles * 0.7  # 70% success threshold
        
        except Exception as e:
            print(f"❌ Performance test error: {e}")
            return False
    
    def optimization_analysis(self):
        """Analyze performance data and provide optimization recommendations."""
        self.print_header("Performance Analysis & Optimization")
        
        if not any(self.performance_data.values()):
            print("❌ No performance data available for analysis")
            return
        
        print("📊 Performance Metrics Analysis:")
        
        # Detection performance
        if self.performance_data['detection_times']:
            detection_times_ms = [t * 1000 for t in self.performance_data['detection_times']]
            avg_detection = sum(detection_times_ms) / len(detection_times_ms)
            print(f"\n🔍 Tag Detection Performance:")
            print(f"   Average detection time: {avg_detection:.1f}ms")
            
            if avg_detection < 50:
                print(f"   ✅ Excellent detection speed")
            elif avg_detection < 100:
                print(f"   ✅ Good detection speed")
            else:
                print(f"   ⚠️  Slow detection - consider hardware optimization")
        
        # Switching performance
        if self.performance_data['switch_times']:
            switch_times_ms = [t * 1000 for t in self.performance_data['switch_times']]
            avg_switch = sum(switch_times_ms) / len(switch_times_ms)
            print(f"\n🔄 Tag Switching Performance:")
            print(f"   Average switch time: {avg_switch:.1f}ms")
            
            if avg_switch < 50:
                print(f"   ✅ Excellent switching speed")
            elif avg_switch < 100:
                print(f"   ✅ Good switching speed")
            else:
                print(f"   ⚠️  Slow switching - may limit multi-tag applications")
        
        # Overall throughput
        if self.performance_data['cycle_times']:
            cycle_times_ms = [t * 1000 for t in self.performance_data['cycle_times']]
            avg_cycle = sum(cycle_times_ms) / len(cycle_times_ms)
            max_rate = 1000 / avg_cycle
            
            print(f"\n⚡ Overall Throughput:")
            print(f"   Average cycle time: {avg_cycle:.1f}ms")
            print(f"   Theoretical max rate: {max_rate:.1f} operations/second")
            
            if max_rate > 5:
                print(f"   ✅ High-speed multi-tag operations possible")
            elif max_rate > 2:
                print(f"   ✅ Moderate-speed multi-tag operations possible")
            else:
                print(f"   ⚠️  Limited to slow multi-tag operations")
        
        # Optimization recommendations
        print(f"\n💡 PN7160 Optimization Recommendations:")
        
        if self.performance_data['switch_times']:
            avg_switch_ms = sum([t * 1000 for t in self.performance_data['switch_times']]) / len(self.performance_data['switch_times'])
            
            if avg_switch_ms > 100:
                print(f"   🔧 Switch time optimization:")
                print(f"      • Reduce polling intervals (currently using 100ms)")
                print(f"      • Check NFC configuration for optimal discovery settings")
                print(f"      • Ensure proper tag positioning for reliable detection")
            
            print(f"   🔧 General optimizations:")
            print(f"      • Use 20ms polling for detection, 100ms for switching")
            print(f"      • Batch operations when possible to reduce overhead")
            print(f"      • Consider tag positioning for optimal RF coupling")
            print(f"      • Monitor for RF interference from other devices")
    
    def run(self, min_tags: int = 2, cycles: int = 10, timeout: int = 30):
        """Run the complete PN7160 fast switching performance test."""
        print("⚡ PN7160 Fast Tag Switching Performance Tool")
        print("=" * 55)
        print("This tool tests and optimizes the PN7160's sequential tag")
        print("switching performance for high-speed multi-tag applications.")
        print("\nIt measures:")
        print("• Tag detection speed during anti-collision")
        print("• selectNextTag() switching performance")
        print("• Overall throughput and cycle times")
        print("• Optimization recommendations\n")
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("⚠️  Warning: This tool typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        success = False
        
        try:
            # Fast discovery scan
            detected_tags = self.fast_discovery_scan(min_tags, timeout//2)
            
            if len(detected_tags) >= min_tags:
                print(f"\n✅ Found {len(detected_tags)} tags - proceeding to performance test")
                
                # Performance switching test
                switching_success = self.performance_switching_test(cycles, timeout//2)
                
                # Analysis and optimization
                self.optimization_analysis()
                
                success = switching_success
            else:
                print(f"\n❌ Only found {len(detected_tags)} tags (need {min_tags})")
                print(f"   Position more tags near the reader and try again")
                return False
            
        except nfc_reader.NFCInitializationError as e:
            print(f"❌ NFC initialization failed: {e}")
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
        
        # Final assessment
        if success:
            print(f"\n✅ PN7160 fast switching test completed successfully!")
            print(f"\n🎯 Your PN7160 is capable of high-performance multi-tag operations")
        else:
            print(f"\n⚠️  PN7160 fast switching test completed with limitations")
            print(f"\n💡 Consider optimizing hardware setup and NFC configuration")
        
        return success

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="PN7160 Fast Tag Switching Performance Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool tests and optimizes the PN7160's tag switching performance for 
high-speed multi-tag applications like inventory management or rapid scanning.

Performance targets:
• Detection: <50ms per tag (excellent), <100ms (good)
• Switching: <50ms per switch (excellent), <100ms (good)  
• Throughput: >5 ops/sec (high-speed), >2 ops/sec (moderate)

Examples:
  %(prog)s --min-tags 3 --cycles 20      # Standard performance test
  %(prog)s --min-tags 5 --cycles 50      # Intensive performance test
  %(prog)s --timeout 60                  # Extended test duration
        """
    )
    
    parser.add_argument('--min-tags', type=int, default=2,
                       help='Minimum number of tags needed for test (default: 2)')
    parser.add_argument('--cycles', type=int, default=10,
                       help='Number of switching cycles to test (default: 10)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Total test timeout in seconds (default: 30)')
    
    args = parser.parse_args()
    
    if args.min_tags < 2:
        print("❌ Minimum tags must be at least 2 for switching tests")
        return 1
    
    if args.cycles < 5:
        print("❌ Cycles must be at least 5 for meaningful performance data")
        return 1
    
    tool = PN7160FastSwitch()
    success = tool.run(
        min_tags=args.min_tags,
        cycles=args.cycles,
        timeout=args.timeout
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())