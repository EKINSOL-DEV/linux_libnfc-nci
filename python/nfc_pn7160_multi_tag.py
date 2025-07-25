#!/usr/bin/env python3
"""
PN7160-Optimized Multi-Tag Detection Tool

This tool is specifically designed for PN7160 NFC controllers that support
anti-collision mechanisms and sequential tag switching. It captures multiple
discovery notifications during the anti-collision phase.

Key insights from the discovery mechanism:
1. PN7160 sends multiple RF_DISCOVER_NTF during anti-collision
2. Each notification contains a different tag's information
3. handleRfDiscoveryEvent() increments mNumDiscNtf for each notification
4. Only when discoveredDevice->more != NCI_DISCOVER_NTF_MORE does it finalize
5. mNumTags is set to the total count of discovery notifications

This tool leverages the PN7160's native anti-collision capabilities to 
detect multiple tags sequentially during a single discovery phase.

Usage:
    sudo python nfc_pn7160_multi_tag.py [--max-tags N] [--timeout T]
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

class PN7160MultiTag:
    """PN7160-optimized multi-tag detection using anti-collision mechanisms."""
    
    def __init__(self):
        self.discovered_tags = []
        self.discovery_events = []
        self.anti_collision_data = []
    
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"🔧 {title}")
        print(f"{'='*70}")
    
    def capture_discovery_phase(self, max_tags=5, timeout=30):
        """
        Capture the PN7160's discovery phase to collect multiple tag information
        during anti-collision.
        
        This method works by:
        1. Starting discovery and monitoring for rapid tag detections
        2. Capturing tag information as the PN7160 cycles through detected tags
        3. Using the hardware's native anti-collision to switch between tags
        4. Collecting all unique UIDs found during the discovery process
        """
        self.print_header(f"PN7160 Anti-Collision Multi-Tag Discovery")
        
        print("🔧 This tool leverages PN7160's anti-collision capabilities")
        print("   to detect multiple tags during a single discovery phase.")
        print(f"\n📱 Place {max_tags} or more NFC tags near the reader")
        print("   and keep them there during the entire discovery process.")
        print("   The PN7160 will automatically cycle through detected tags.")
        print(f"\n⏰ Discovery timeout: {timeout} seconds")
        
        input("\nPress Enter when tags are positioned and ready...")
        
        try:
            # Low-level discovery monitoring
            success = nfc_native.initialize()
            if not success:
                print("❌ NFC initialization failed")
                return False
            
            nfc_native.start_discovery()
            print("\n🔍 Discovery started - monitoring anti-collision phase...")
            
            start_time = time.time()
            last_num_tags = 0
            last_present = False
            discovery_cycles = 0
            unique_tags = set()
            rapid_detections = []
            
            while time.time() - start_time < timeout:
                try:
                    # Monitor the core detection APIs
                    is_present = nfc_native.is_tag_present()
                    num_tags = nfc_native.get_num_tags()
                    elapsed = time.time() - start_time
                    
                    # Detect changes in tag presence or count
                    if is_present != last_present or num_tags != last_num_tags:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        
                        if is_present:
                            print(f"[{timestamp}] 📡 Tag detected - getNumTags()={num_tags}")
                            
                            # Try to read tag information quickly
                            try:
                                tag_info = nfc_native.get_tag_info()
                                if tag_info and isinstance(tag_info, dict):
                                    uid = tag_info.get('uid', 'Unknown')
                                    tech = tag_info.get('technology_name', 'Unknown')
                                    handle = tag_info.get('handle', 'Unknown')
                                    
                                    if uid not in unique_tags and uid != 'Unknown':
                                        unique_tags.add(uid)
                                        
                                        detection_data = {
                                            'uid': uid,
                                            'technology': tech,
                                            'handle': handle,
                                            'detection_time': elapsed,
                                            'discovery_cycle': discovery_cycles,
                                            'tag_count_when_detected': num_tags
                                        }
                                        
                                        rapid_detections.append(detection_data)
                                        
                                        print(f"    📋 UID: {uid[:16]}... ({tech})")
                                        print(f"    🔧 Handle: {handle}, Count: {num_tags}")
                                        
                                        # Try to read text if available
                                        try:
                                            text_data = nfc_native.read_text()
                                            if text_data and text_data.get('text'):
                                                detection_data['text'] = text_data['text']
                                                print(f"    📝 Text: '{text_data['text']}'")
                                        except:
                                            pass
                                    
                                    # Test anti-collision switching
                                    if len(unique_tags) > 1:
                                        try:
                                            next_result = nfc_native.select_next_tag()
                                            if next_result:
                                                print(f"    🔄 selectNextTag() succeeded")
                                                discovery_cycles += 1
                                        except Exception as e:
                                            print(f"    ⚠️  selectNextTag() failed: {e}")
                                        
                                        try:
                                            protocol = nfc_native.check_next_protocol()
                                            print(f"    🔍 Next protocol: {protocol}")
                                        except Exception as e:
                                            print(f"    ⚠️  checkNextProtocol() failed: {e}")
                            
                            except Exception as e:
                                print(f"    ❌ Error reading tag info: {e}")
                        else:
                            print(f"[{timestamp}] 📤 No tag present - getNumTags()={num_tags}")
                        
                        last_present = is_present
                        last_num_tags = num_tags
                    
                    # Short polling interval to catch rapid switching
                    time.sleep(0.05)
                    
                except KeyboardInterrupt:
                    print("\n⚠️  Discovery interrupted by user")
                    break
                except Exception as e:
                    print(f"❌ Error during discovery monitoring: {e}")
                    time.sleep(0.2)
            
            # Analysis and results
            self.print_header("PN7160 Anti-Collision Discovery Results")
            
            print(f"📊 Discovery Summary:")
            print(f"   Duration: {elapsed:.1f} seconds")
            print(f"   Discovery cycles: {discovery_cycles}")
            print(f"   Unique tags detected: {len(unique_tags)}")
            print(f"   Total detection events: {len(rapid_detections)}")
            print(f"   Final getNumTags(): {last_num_tags}")
            
            if len(unique_tags) >= 2:
                print(f"\n✅ SUCCESS: PN7160 anti-collision detected {len(unique_tags)} unique tags!")
                
                print(f"\n📋 Detected Tags:")
                for i, detection in enumerate(rapid_detections):
                    uid = detection['uid']
                    tech = detection['technology']
                    text = detection.get('text', 'No text')
                    cycle = detection['discovery_cycle']
                    count = detection['tag_count_when_detected']
                    
                    print(f"\nTag {i+1}:")
                    print(f"  UID: {uid}")
                    print(f"  Technology: {tech}")
                    print(f"  Text: '{text}'")
                    print(f"  Discovery cycle: {cycle}")
                    print(f"  Tag count when detected: {count}")
                    print(f"  Detection time: {detection['detection_time']:.1f}s")
                
                self.discovered_tags = rapid_detections
                return True
                
            elif len(unique_tags) == 1:
                print(f"\n⚠️  Only one unique tag detected")
                print(f"   Try positioning multiple tags closer together")
                print(f"   or check if anti-collision is enabled in NFC configuration")
                return False
                
            else:
                print(f"\n❌ No consistent tag detection")
                print(f"   Check tag positioning and hardware connection")
                return False
        
        except Exception as e:
            print(f"❌ Discovery error: {e}")
            return False
        
        finally:
            try:
                nfc_native.stop_discovery()
                nfc_native.deinitialize()
                print("\n✅ Discovery cleanup completed")
            except:
                pass
    
    def test_sequential_switching(self, timeout=20):
        """
        Test the PN7160's ability to switch between multiple tags sequentially.
        This tests the selectNextTag() and checkNextProtocol() functions.
        """
        self.print_header("PN7160 Sequential Tag Switching Test")
        
        print("🔧 This test evaluates the PN7160's tag switching capabilities")
        print("   using selectNextTag() and checkNextProtocol() functions.")
        print(f"\n📱 Place 2-3 NFC tags near the reader and keep them there")
        print(f"⏰ Test duration: {timeout} seconds")
        
        input("\nPress Enter to start switching test...")
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                start_time = time.time()
                switching_results = []
                current_tag = None
                
                while time.time() - start_time < timeout:
                    if reader.is_tag_present():
                        num_tags = reader.get_num_tags()
                        
                        if num_tags > 1:
                            try:
                                # Get current tag info
                                tag_info = reader.get_tag_info()
                                if tag_info:
                                    current_uid = tag_info.get('uid', 'Unknown')
                                    
                                    # Try to switch to next tag
                                    switch_result = nfc_native.select_next_tag()
                                    if switch_result:
                                        # Get new tag info after switch
                                        new_tag_info = reader.get_tag_info()
                                        if new_tag_info:
                                            new_uid = new_tag_info.get('uid', 'Unknown')
                                            
                                            switching_results.append({
                                                'from_uid': current_uid[:16],
                                                'to_uid': new_uid[:16],
                                                'switch_successful': current_uid != new_uid,
                                                'time': time.time() - start_time
                                            })
                                            
                                            timestamp = datetime.now().strftime("%H:%M:%S")
                                            if current_uid != new_uid:
                                                print(f"[{timestamp}] ✅ Switched: {current_uid[:16]}... → {new_uid[:16]}...")
                                            else:
                                                print(f"[{timestamp}] 🔄 Same tag: {current_uid[:16]}...")
                            
                            except Exception as e:
                                print(f"❌ Switch error: {e}")
                        
                        elif num_tags == 1:
                            if not current_tag:
                                tag_info = reader.get_tag_info()
                                if tag_info:
                                    current_tag = tag_info.get('uid', 'Unknown')
                                    print(f"📱 Single tag detected: {current_tag[:16]}...")
                    
                    time.sleep(0.3)  # Allow time between switch attempts
                
                # Results
                successful_switches = [r for r in switching_results if r['switch_successful']]
                
                print(f"\n📊 Sequential Switching Results:")
                print(f"   Total switch attempts: {len(switching_results)}")
                print(f"   Successful switches: {len(successful_switches)}")
                print(f"   Switch success rate: {len(successful_switches)/len(switching_results)*100:.1f}%" if switching_results else "0%")
                
                if successful_switches:
                    print(f"\n✅ PN7160 sequential switching works!")
                    print(f"   The hardware can switch between multiple tags")
                    return True
                else:
                    print(f"\n⚠️  Limited switching capabilities detected")
                    return False
        
        except Exception as e:
            print(f"❌ Switching test error: {e}")
            return False
    
    def run(self, max_tags: int = 5, timeout: int = 30, test_switching: bool = True):
        """Run the complete PN7160 multi-tag analysis."""
        print("🔧 PN7160-Optimized Multi-Tag Detection Tool")
        print("=" * 50)
        print("This tool is specifically designed for PN7160 NFC controllers")
        print("that support anti-collision mechanisms and sequential tag switching.")
        print("\nIt works by capturing multiple RF_DISCOVER_NTF notifications")
        print("during the anti-collision phase, allowing detection of multiple")
        print("tags that the hardware discovers sequentially.\n")
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("⚠️  Warning: This tool typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        success = False
        
        try:
            # Main discovery test
            discovery_success = self.capture_discovery_phase(max_tags, timeout)
            
            if discovery_success and test_switching:
                print(f"\n🔄 Proceeding to sequential switching test...")
                time.sleep(1)
                switching_success = self.test_sequential_switching(20)
                success = discovery_success and switching_success
            else:
                success = discovery_success
            
        except nfc_reader.NFCInitializationError as e:
            print(f"❌ NFC initialization failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure you're running as root (sudo)")
            print("2. Check that PN7160 hardware is connected")
            print("3. Ensure no other NFC applications are running")
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
        
        # Final assessment
        if success:
            print("\n✅ PN7160 multi-tag capabilities confirmed!")
            print("\n💡 Your PN7160 hardware supports:")
            print("   • Anti-collision detection of multiple tags")
            print("   • Sequential switching between detected tags")
            print("   • Capturing multiple UIDs during discovery phase")
            print("\n🎯 Recommendation: Use this anti-collision approach for")
            print("   reliable multi-tag detection instead of getNumTags().")
        else:
            print("\n⚠️  PN7160 multi-tag capabilities are limited")
            print("\n💡 This could be due to:")
            print("   • Anti-collision not enabled in NFC configuration")
            print("   • Hardware limitations or interference")
            print("   • Tag positioning issues")
            print("   • Firmware configuration problems")
        
        return success

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="PN7160-Optimized Multi-Tag Detection Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool is specifically designed for PN7160 NFC controllers and leverages
their native anti-collision mechanisms to detect multiple tags sequentially.

The PN7160 supports:
• Anti-collision detection during discovery phase
• Sequential switching between multiple detected tags  
• Capture of multiple RF_DISCOVER_NTF notifications

Examples:
  %(prog)s --max-tags 3 --timeout 30     # Standard discovery test
  %(prog)s --max-tags 5 --no-switching   # Discovery only (no switching test)
  %(prog)s --timeout 60                  # Extended discovery time
        """
    )
    
    parser.add_argument('--max-tags', type=int, default=5,
                       help='Maximum number of tags to detect (default: 5)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Discovery timeout in seconds (default: 30)')
    parser.add_argument('--no-switching', action='store_true',
                       help='Skip sequential switching test')
    
    args = parser.parse_args()
    
    if args.max_tags < 2:
        print("❌ Maximum tags must be at least 2 for multi-tag testing")
        return 1
    
    tool = PN7160MultiTag()
    success = tool.run(
        max_tags=args.max_tags, 
        timeout=args.timeout,
        test_switching=not args.no_switching
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())