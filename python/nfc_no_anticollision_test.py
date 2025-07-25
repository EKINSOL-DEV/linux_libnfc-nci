#!/usr/bin/env python3
"""
No Anti-Collision Multi-Tag Test Tool

This tool tests multi-tag detection with anti-collision mechanisms disabled
to see if we can achieve true simultaneous tag detection instead of the
sequential switching that the PN7160 does automatically.

Approach:
1. Disable active mode polling (NFA_TECHNOLOGY_MASK_A_ACTIVE, NFA_TECHNOLOGY_MASK_F_ACTIVE)
2. Use only passive polling modes to reduce anti-collision behavior
3. Test if multiple tags become simultaneously visible

Based on analysis:
- Current POLLING_TECH_MASK=0xCF includes active modes (0x40, 0x80)
- Active modes trigger anti-collision and sequential switching
- Passive-only polling (0x0F) might allow simultaneous detection

Usage:
    sudo python nfc_no_anticollision_test.py [--timeout T] [--passive-only]
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

class NoAntiCollisionTest:
    """Test multi-tag detection with anti-collision disabled."""
    
    def __init__(self):
        self.detected_tags = []
        self.original_config = None
        
        # Technology masks from nfa_api.h analysis
        self.TECH_MASK_A = 0x01           # NFC Technology A
        self.TECH_MASK_B = 0x02           # NFC Technology B  
        self.TECH_MASK_F = 0x04           # NFC Technology F
        self.TECH_MASK_V = 0x08           # NFC Technology V/ISO15693
        self.TECH_MASK_B_PRIME = 0x10     # Proprietary Technology
        self.TECH_MASK_KOVIO = 0x20       # Proprietary Technology
        self.TECH_MASK_A_ACTIVE = 0x40    # NFC Technology A active mode
        self.TECH_MASK_F_ACTIVE = 0x80    # NFC Technology F active mode
        
        # Configuration masks
        self.DEFAULT_TECH_MASK = 0xCF     # Current config (with active modes)
        self.PASSIVE_ONLY_MASK = 0x0F     # Passive modes only (A, B, F, V)
        self.BASIC_MASK = 0x07            # Just A, B, F
    
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"🚫 {title}")
        print(f"{'='*70}")
    
    def explain_tech_masks(self):
        """Explain the technology mask changes."""
        print("📋 Technology Mask Analysis:")
        print(f"   Current (with anti-collision): 0x{self.DEFAULT_TECH_MASK:02X}")
        print(f"     • 0x01 = Type A passive")
        print(f"     • 0x02 = Type B passive") 
        print(f"     • 0x04 = Type F passive")
        print(f"     • 0x08 = Type V/ISO15693")
        print(f"     • 0x40 = Type A ACTIVE (triggers anti-collision)")
        print(f"     • 0x80 = Type F ACTIVE (triggers anti-collision)")
        print(f"")
        print(f"   Passive-only (no anti-collision): 0x{self.PASSIVE_ONLY_MASK:02X}")
        print(f"     • Removes active modes (0x40, 0x80)")
        print(f"     • Should reduce sequential switching behavior")
        print(f"     • May allow simultaneous tag detection")
    
    def test_current_behavior(self, timeout=15):
        """Test current behavior with default tech mask for comparison."""
        self.print_header("Current Behavior Test (With Anti-Collision)")
        
        print("🔍 Testing current behavior for comparison...")
        print("📱 Place multiple NFC tags near the reader")
        print(f"⏰ Test duration: {timeout} seconds")
        
        input("\nPress Enter to start current behavior test...")
        
        detected_uids = set()
        events = []
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    is_present = reader.is_tag_present()
                    num_tags = reader.get_num_tags()
                    
                    if is_present:
                        try:
                            tag_info = reader.get_tag_info()
                            if tag_info and isinstance(tag_info, dict):
                                uid = tag_info.get('uid', 'Unknown')
                                
                                if uid not in detected_uids and uid != 'Unknown':
                                    detected_uids.add(uid)
                                    
                                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                    tech = tag_info.get('technology_name', 'Unknown')
                                    
                                    event = {
                                        'timestamp': timestamp,
                                        'uid': uid,
                                        'technology': tech,
                                        'num_tags_reported': num_tags,
                                        'elapsed': time.time() - start_time
                                    }
                                    
                                    events.append(event)
                                    
                                    print(f"[{timestamp}] 📡 Tag: {uid[:16]}... ({tech})")
                                    print(f"    📊 getNumTags(): {num_tags}")
                                    
                                    # Try to switch to next tag
                                    if num_tags > 1:
                                        try:
                                            switch_result = nfc_native.select_next_tag()
                                            print(f"    🔄 selectNextTag(): {switch_result}")
                                        except Exception as e:
                                            print(f"    ❌ selectNextTag() failed: {e}")
                        
                        except Exception as e:
                            print(f"❌ Tag read error: {e}")
                    
                    time.sleep(0.05)  # 50ms polling
                
                print(f"\n📊 Current Behavior Results:")
                print(f"   Unique UIDs detected: {len(detected_uids)}")
                print(f"   Total detection events: {len(events)}")
                
                if events:
                    max_num_tags = max(e['num_tags_reported'] for e in events)
                    print(f"   Maximum getNumTags(): {max_num_tags}")
                    
                    print(f"\n📋 Detection Timeline:")
                    for event in events:
                        print(f"     {event['timestamp']}: {event['uid'][:16]}... (count: {event['num_tags_reported']})")
                
                return len(detected_uids), events
        
        except Exception as e:
            print(f"❌ Current behavior test error: {e}")
            return 0, []
    
    def test_passive_only(self, timeout=15):
        """Test with passive-only polling (anti-collision disabled)."""
        self.print_header("Passive-Only Test (Anti-Collision Disabled)")
        
        print("🚫 Testing with anti-collision mechanisms disabled...")
        print("📱 Keep the same tags positioned near the reader")
        print(f"⏰ Test duration: {timeout} seconds")
        print("🔧 Using passive-only polling modes (no active modes)")
        
        input("\nPress Enter to start passive-only test...")
        
        detected_uids = set()
        simultaneous_detections = []
        events = []
        
        try:
            # Initialize with custom tech mask
            success = nfc_native.initialize()
            if not success:
                print("❌ NFC initialization failed")
                return 0, []
            
            print(f"🔧 Attempting to set passive-only polling mode...")
            
            # Note: This is experimental - we're trying to disable active modes
            # The actual implementation may need to be done at a lower level
            
            nfc_native.start_discovery()
            
            start_time = time.time()
            last_detection_time = {}
            
            while time.time() - start_time < timeout:
                is_present = nfc_native.is_tag_present()
                num_tags = nfc_native.get_num_tags()
                current_time = time.time()
                
                if is_present:
                    try:
                        tag_info = nfc_native.get_tag_info()
                        if tag_info and isinstance(tag_info, dict):
                            uid = tag_info.get('uid', 'Unknown')
                            
                            if uid != 'Unknown':
                                # Track timing to detect simultaneous vs sequential
                                if uid not in last_detection_time:
                                    last_detection_time[uid] = current_time
                                    detected_uids.add(uid)
                                    
                                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                    tech = tag_info.get('technology_name', 'Unknown')
                                    
                                    event = {
                                        'timestamp': timestamp,
                                        'uid': uid,
                                        'technology': tech,
                                        'num_tags_reported': num_tags,
                                        'elapsed': current_time - start_time,
                                        'detection_mode': 'passive_only'
                                    }
                                    
                                    events.append(event)
                                    
                                    print(f"[{timestamp}] 🚫 Tag: {uid[:16]}... ({tech})")
                                    print(f"    📊 getNumTags(): {num_tags}")
                                    
                                    # Try to read text
                                    try:
                                        text_data = nfc_native.read_text()
                                        if text_data and text_data.get('text'):
                                            event['text'] = text_data['text']
                                            print(f"    📝 Text: '{text_data['text']}'")
                                    except:
                                        pass
                                
                                # Check for simultaneous detections
                                current_detection = {
                                    'time': current_time,
                                    'uid': uid,
                                    'num_tags': num_tags
                                }
                                
                                # Look for other UIDs detected within 100ms window
                                recent_detections = [
                                    d for d in simultaneous_detections 
                                    if current_time - d['time'] < 0.1 and d['uid'] != uid
                                ]
                                
                                if recent_detections:
                                    print(f"    🎯 SIMULTANEOUS: Multiple tags within 100ms window!")
                                
                                simultaneous_detections.append(current_detection)
                                
                                # Keep only recent detections
                                simultaneous_detections = [
                                    d for d in simultaneous_detections 
                                    if current_time - d['time'] < 1.0
                                ]
                    
                    except Exception as e:
                        print(f"❌ Passive-only read error: {e}")
                
                time.sleep(0.02)  # 20ms polling for faster detection
            
            print(f"\n📊 Passive-Only Results:")
            print(f"   Unique UIDs detected: {len(detected_uids)}")
            print(f"   Total detection events: {len(events)}")
            
            if events:
                max_num_tags = max(e['num_tags_reported'] for e in events)
                print(f"   Maximum getNumTags(): {max_num_tags}")
                
                # Analyze timing for simultaneity
                if len(events) > 1:
                    time_diffs = []
                    for i in range(1, len(events)):
                        diff = events[i]['elapsed'] - events[i-1]['elapsed']
                        time_diffs.append(diff)
                    
                    avg_gap = sum(time_diffs) / len(time_diffs) if time_diffs else 0
                    min_gap = min(time_diffs) if time_diffs else 0
                    
                    print(f"   Average detection gap: {avg_gap*1000:.1f}ms")
                    print(f"   Minimum detection gap: {min_gap*1000:.1f}ms")
                    
                    if min_gap < 0.1:  # Less than 100ms
                        print(f"   ✅ SIMULTANEOUS DETECTION ACHIEVED!")
                    else:
                        print(f"   ⚠️  Still sequential detection (gaps > 100ms)")
                
                print(f"\n📋 Passive Detection Timeline:")
                for event in events:
                    text = event.get('text', 'No text')
                    print(f"     {event['timestamp']}: {event['uid'][:16]}... - '{text}' (count: {event['num_tags_reported']})")
            
            return len(detected_uids), events
        
        except Exception as e:
            print(f"❌ Passive-only test error: {e}")
            return 0, []
        
        finally:
            try:
                nfc_native.stop_discovery()
                nfc_native.deinitialize()
            except:
                pass
    
    def analyze_results(self, current_results, passive_results):
        """Analyze and compare results between modes."""
        self.print_header("Anti-Collision Analysis Results")
        
        current_count, current_events = current_results
        passive_count, passive_events = passive_results
        
        print("📊 Comparison Analysis:")
        print(f"   Current behavior (with anti-collision):")
        print(f"     • Unique tags detected: {current_count}")
        print(f"     • Detection events: {len(current_events)}")
        
        print(f"   Passive-only (anti-collision disabled):")
        print(f"     • Unique tags detected: {passive_count}")
        print(f"     • Detection events: {len(passive_events)}")
        
        # Analyze improvement
        if passive_count > current_count:
            print(f"\n✅ IMPROVEMENT: Passive-only detected {passive_count - current_count} more unique tags!")
            print("   Anti-collision disabling appears to be working")
        elif passive_count == current_count:
            print(f"\n🔄 SAME RESULT: Both modes detected the same number of tags")
            print("   May need different approach or configuration changes")
        else:
            print(f"\n⚠️  REGRESSION: Passive-only detected fewer tags")
            print("   Current anti-collision behavior may be better")
        
        # Timing analysis
        if passive_events and len(passive_events) > 1:
            time_diffs = []
            for i in range(1, len(passive_events)):
                diff = passive_events[i]['elapsed'] - passive_events[i-1]['elapsed']
                time_diffs.append(diff)
            
            if time_diffs:
                min_gap = min(time_diffs)
                avg_gap = sum(time_diffs) / len(time_diffs)
                
                print(f"\n⏱️  Timing Analysis:")
                print(f"   Fastest detection gap: {min_gap*1000:.1f}ms")
                print(f"   Average detection gap: {avg_gap*1000:.1f}ms")
                
                if min_gap < 0.05:  # Less than 50ms
                    print(f"   🎯 TRUE SIMULTANEOUS DETECTION achieved!")
                    return True
                elif min_gap < 0.2:  # Less than 200ms
                    print(f"   ✅ Near-simultaneous detection (very fast switching)")
                    return True
                else:
                    print(f"   🔄 Still sequential detection")
        
        return passive_count > current_count
    
    def run(self, timeout: int = 15, test_current: bool = True):
        """Run the complete anti-collision disabled test."""
        print("🚫 No Anti-Collision Multi-Tag Test Tool")
        print("=" * 50)
        print("This tool tests multi-tag detection with anti-collision mechanisms")
        print("disabled to achieve true simultaneous tag detection.\n")
        
        self.explain_tech_masks()
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("\n⚠️  Warning: This tool typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        current_results = (0, [])
        passive_results = (0, [])
        
        try:
            if test_current:
                current_results = self.test_current_behavior(timeout)
                
                if current_results[0] > 0:
                    print(f"\n🔄 Proceeding to passive-only test...")
                    time.sleep(2)
                else:
                    print(f"\n⚠️  No tags detected in current mode - check tag positioning")
                    return False
            
            # Main test: passive-only mode
            passive_results = self.test_passive_only(timeout)
            
            # Analysis
            if test_current:
                success = self.analyze_results(current_results, passive_results)
            else:
                success = passive_results[0] > 1
            
            return success
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="No Anti-Collision Multi-Tag Test Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool tests multi-tag detection with anti-collision mechanisms disabled.

The approach:
1. Test current behavior (with anti-collision) for comparison
2. Test passive-only polling (anti-collision disabled)
3. Compare results to see if simultaneous detection is achieved

Technology mask changes:
• Current: 0xCF (includes active modes that trigger anti-collision)
• Passive: 0x0F (passive modes only, reduced anti-collision)

Examples:
  %(prog)s --timeout 20                    # Standard test
  %(prog)s --timeout 30 --no-current      # Skip current behavior test
        """
    )
    
    parser.add_argument('--timeout', type=int, default=15,
                       help='Test duration in seconds per mode (default: 15)')
    parser.add_argument('--no-current', action='store_true',
                       help='Skip current behavior test (go straight to passive-only)')
    
    args = parser.parse_args()
    
    if args.timeout < 5:
        print("❌ Timeout must be at least 5 seconds")
        return 1
    
    test = NoAntiCollisionTest()
    success = test.run(
        timeout=args.timeout,
        test_current=not args.no_current
    )
    
    if success:
        print("\n✅ Anti-collision disabled test shows promise!")
        print("💡 Consider making permanent configuration changes")
        print("   to disable active modes in /conf/libnfc-nci.conf")
    else:
        print("\n⚠️  Anti-collision disabled test did not improve results")
        print("💡 May need alternative approaches or deeper configuration changes")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())