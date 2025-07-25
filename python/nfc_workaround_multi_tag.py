#!/usr/bin/env python3
"""
NFC Multi-Tag Workaround Demo

This demo works around the getNumTags() limitation by using a different
approach to multi-tag detection that doesn't rely on the broken getNumTags() API.

The approach:
1. Use is_tag_present() which works correctly
2. When a tag is detected, quickly read it and store the data
3. Use rapid tag switching to detect multiple tags sequentially
4. Provide a better user experience for hardware that doesn't support true multi-tag

Usage:
    sudo python nfc_workaround_multi_tag.py [--mode MODE]
"""

import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import nfc_reader
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

class WorkaroundMultiTag:
    """Multi-tag detection that works around the getNumTags() limitation."""
    
    def __init__(self):
        self.detected_tags = []
        self.seen_uids = set()
    
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"🔧 {title}")
        print(f"{'='*70}")
    
    def rapid_multi_tag_detection(self, target_tags=3, timeout=30):
        """
        Rapid multi-tag detection that works around getNumTags() limitation.
        
        This method works by:
        1. Detecting when a tag arrives (is_tag_present() = True)
        2. Quickly reading the tag data
        3. Waiting for the tag to be removed
        4. Repeating for the next tag
        """
        self.print_header(f"Workaround Multi-Tag Detection ({target_tags} tags)")
        
        print("🔧 This method works around the getNumTags() limitation")
        print("   by using rapid sequential detection instead.")
        print(f"\n📱 Place and remove {target_tags} different NFC tags one at a time:")
        print("   1. Place tag 1 → wait for confirmation → remove tag 1")
        print("   2. Place tag 2 → wait for confirmation → remove tag 2")
        print("   3. Continue until done...")
        print(f"\n⏰ You have {timeout} seconds total.")
        
        input("\nPress Enter when ready to start...")
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                start_time = time.time()
                last_tag_present = False
                current_tag_data = None
                
                while time.time() - start_time < timeout and len(self.detected_tags) < target_tags:
                    is_present = reader.is_tag_present()
                    elapsed = time.time() - start_time
                    
                    # Tag arrival
                    if is_present and not last_tag_present:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"\n[{timestamp}] 📱 Tag detected! Reading...")
                        
                        try:
                            # Quick read of tag info and text
                            tag_info = reader.get_tag_info()
                            text_data = reader.read_text()
                            
                            if tag_info and isinstance(tag_info, dict):
                                uid = tag_info.get('uid', 'Unknown')
                                
                                # Check if this is a new tag
                                if uid not in self.seen_uids:
                                    self.seen_uids.add(uid)
                                    
                                    # Combine tag info and text data
                                    combined_data = {**tag_info}
                                    if text_data:
                                        combined_data.update(text_data)
                                    
                                    combined_data['detection_order'] = len(self.detected_tags) + 1
                                    combined_data['detection_time'] = elapsed
                                    
                                    self.detected_tags.append(combined_data)
                                    current_tag_data = combined_data
                                    
                                    # Display tag info
                                    tech = tag_info.get('technology_name', 'Unknown')
                                    text = text_data.get('text', 'No text') if text_data else 'No text'
                                    
                                    print(f"✅ Tag {len(self.detected_tags)}: {tech}")
                                    print(f"   Text: '{text}'")
                                    print(f"   UID: {uid[:16]}...")
                                    
                                    if len(self.detected_tags) < target_tags:
                                        print(f"\n🔄 Remove this tag and place tag {len(self.detected_tags)+1}")
                                        print(f"   {target_tags - len(self.detected_tags)} more tags needed")
                                    else:
                                        print(f"\n🎉 All {target_tags} tags detected!")
                                        break
                                else:
                                    print(f"🔄 Already seen this tag (UID: {uid[:16]}...)")
                                    print("   Try a different tag")
                            else:
                                print("⚠️  Could not read tag info")
                        
                        except Exception as e:
                            print(f"❌ Error reading tag: {e}")
                    
                    # Tag departure
                    elif not is_present and last_tag_present:
                        if current_tag_data:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            print(f"[{timestamp}] 📤 Tag removed")
                            current_tag_data = None
                    
                    last_tag_present = is_present
                    time.sleep(0.05)  # 50ms polling
                
                # Results
                if len(self.detected_tags) >= target_tags:
                    print(f"\n🎉 SUCCESS: Detected all {target_tags} target tags!")
                elif len(self.detected_tags) > 0:
                    print(f"\n⚠️  Partial success: Detected {len(self.detected_tags)} of {target_tags} tags")
                else:
                    print(f"\n❌ No tags detected")
                
                return len(self.detected_tags) >= target_tags
                
        except Exception as e:
            print(f"❌ Error during multi-tag detection: {e}")
            return False
    
    def simultaneous_placement_test(self, timeout=20):
        """
        Test what happens when multiple tags are placed simultaneously.
        
        This helps understand if the hardware can detect multiple tags
        even if getNumTags() doesn't work.
        """
        self.print_header("Simultaneous Placement Test")
        
        print("🧪 This test checks what happens when multiple tags")
        print("   are placed near the reader at the same time.")
        print(f"\n📱 Place 2-3 NFC tags near the reader simultaneously")
        print("   and keep them there for the entire test period.")
        
        input(f"\nPress Enter to start {timeout} second test...")
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                start_time = time.time()
                measurements = []
                last_measurement = None
                
                while time.time() - start_time < timeout:
                    is_present = reader.is_tag_present()
                    
                    measurement = {
                        'time': time.time() - start_time,
                        'is_present': is_present,
                        'tag_info': None,
                        'text_data': None
                    }
                    
                    if is_present:
                        try:
                            # Try to read tag info
                            tag_info = reader.get_tag_info()
                            if tag_info and isinstance(tag_info, dict):
                                measurement['tag_info'] = tag_info
                                uid = tag_info.get('uid', 'Unknown')
                                tech = tag_info.get('technology_name', 'Unknown')
                                
                                # Only print when UID changes (different tag detected)
                                if not last_measurement or last_measurement.get('tag_info', {}).get('uid') != uid:
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    print(f"[{timestamp}] Tag: {tech} (UID: {uid[:16]}...)")
                                
                                # Try to read text
                                text_data = reader.read_text()
                                if text_data:
                                    measurement['text_data'] = text_data
                        
                        except Exception as e:
                            print(f"   Error reading tag: {e}")
                    
                    measurements.append(measurement)
                    last_measurement = measurement
                    time.sleep(0.2)  # 200ms intervals
                
                # Analysis
                print(f"\n📊 Test Results:")
                
                present_measurements = [m for m in measurements if m['is_present']]
                unique_uids = set()
                
                for m in present_measurements:
                    if m['tag_info']:
                        uid = m['tag_info'].get('uid')
                        if uid:
                            unique_uids.add(uid)
                
                print(f"   Total measurements: {len(measurements)}")
                print(f"   Tag present: {len(present_measurements)} times")
                print(f"   Unique UIDs detected: {len(unique_uids)}")
                
                if len(unique_uids) > 1:
                    print(f"✅ Hardware can detect multiple different tags!")
                    print(f"   (Just not simultaneously via getNumTags())")
                    for i, uid in enumerate(unique_uids):
                        print(f"     Tag {i+1}: {uid[:16]}...")
                elif len(unique_uids) == 1:
                    print(f"⚠️  Only one unique tag detected")
                    print(f"   Try placing tags at different positions/angles")
                else:
                    print(f"❌ No consistent tag detection")
                
                return len(unique_uids)
                
        except Exception as e:
            print(f"❌ Error during simultaneous test: {e}")
            return 0
    
    def print_summary(self):
        """Print summary of detected tags."""
        if not self.detected_tags:
            print("\nNo tags were detected during this session.")
            return
        
        self.print_header(f"Tag Detection Summary ({len(self.detected_tags)} tags)")
        
        for tag in self.detected_tags:
            order = tag.get('detection_order', '?')
            text = tag.get('text', 'No text')
            uid = tag.get('uid', 'Unknown')
            tech = tag.get('technology_name', 'Unknown')
            detection_time = tag.get('detection_time', 0)
            
            print(f"\nTag {order}:")
            print(f"  Technology: {tech}")
            print(f"  Text: '{text}'")
            print(f"  UID: {uid}")
            print(f"  Detected at: {detection_time:.1f}s")
    
    def run(self, mode: str, target_tags: int = 3):
        """Run the workaround multi-tag demo."""
        print("🔧 NFC Multi-Tag Workaround Demo")
        print("=" * 40)
        print("This demo works around the getNumTags() limitation by using")
        print("alternative detection methods that work with your hardware.\n")
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("⚠️  Warning: This demo typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        success = False
        
        try:
            if mode == 'rapid':
                success = self.rapid_multi_tag_detection(target_tags)
            elif mode == 'simultaneous':
                unique_tags = self.simultaneous_placement_test()
                success = unique_tags >= 2
            elif mode == 'both':
                print("Running both test modes...\n")
                unique_tags = self.simultaneous_placement_test()
                if unique_tags >= 2:
                    print(f"\n✅ Simultaneous test detected {unique_tags} unique tags")
                    print("Proceeding to rapid detection test...\n")
                    success = self.rapid_multi_tag_detection(target_tags)
                else:
                    print(f"\n⚠️  Simultaneous test only detected {unique_tags} unique tags")
                    print("Your hardware may have limited multi-tag capabilities")
                    success = False
            else:
                print(f"❌ Unknown mode: {mode}")
                return False
            
        except nfc_reader.NFCInitializationError as e:
            print(f"❌ NFC initialization failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure you're running as root (sudo)")
            print("2. Check that NFC hardware is connected")
            print("3. Ensure no other NFC applications are running")
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
        
        finally:
            if mode in ['rapid', 'both']:
                self.print_summary()
        
        if success:
            print("\n✅ Multi-tag workaround demo completed successfully!")
            print("\n💡 Recommendation: Use the 'rapid' mode for reliable multi-tag detection")
            print("   with your hardware, rather than relying on getNumTags().")
        else:
            print("\n⚠️  Demo completed with limited success")
            print("\n💡 Your NFC hardware appears to have limited multi-tag capabilities.")
            print("   Consider using single-tag applications or upgrading hardware.")
        
        return success

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="NFC Multi-Tag Workaround Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  rapid         Rapid sequential tag detection (recommended)
  simultaneous  Test simultaneous tag placement capabilities
  both          Run both tests (default)

Examples:
  %(prog)s --mode rapid --target-tags 3    # Detect 3 tags sequentially
  %(prog)s --mode simultaneous              # Test simultaneous capabilities
  %(prog)s --mode both                      # Run comprehensive test
        """
    )
    
    parser.add_argument('--mode', default='both',
                       choices=['rapid', 'simultaneous', 'both'],
                       help='Detection mode (default: both)')
    parser.add_argument('--target-tags', type=int, default=3,
                       help='Number of tags to detect in rapid mode (default: 3)')
    
    args = parser.parse_args()
    
    demo = WorkaroundMultiTag()
    success = demo.run(args.mode, args.target_tags)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())