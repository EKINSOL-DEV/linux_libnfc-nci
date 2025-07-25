#!/usr/bin/env python3
"""
Enhanced Multi-Tag NFC Demo with Fallback Strategies

This enhanced demo includes multiple strategies for multi-tag detection:
1. True simultaneous detection (preferred)
2. Rapid sequential detection (fallback)
3. Manual sequential detection (fallback)
4. Hardware capability detection and adaptation

Usage:
    sudo python nfc_multi_tag_enhanced.py [--mode MODE] [--strategy STRATEGY]

Modes:
    auto        - Auto-detect best strategy and use it
    simultaneous - Try true simultaneous detection
    sequential   - Use rapid sequential detection
    manual       - Manual sequential detection
    test         - Test all strategies and report capabilities

Strategies:
    auto        - Automatically choose best available strategy
    force-sim   - Force simultaneous detection (may fail)
    force-seq   - Force sequential detection
    adaptive    - Adapt based on hardware capabilities
"""

import sys
import time
import argparse
import signal
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import nfc_reader
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

class MultiTagStrategies:
    """Different strategies for multi-tag detection."""
    
    @staticmethod
    def test_hardware_capabilities(reader, timeout=10):
        """Test what multi-tag capabilities the hardware supports."""
        print("🔍 Testing hardware capabilities...")
        
        capabilities = {
            'single_tag': False,
            'getNumTags_works': False,
            'max_simultaneous': 0,
            'selectNextTag_works': False,
            'rapid_sequential': False
        }
        
        # Test 1: Single tag detection
        print("   Testing single tag detection...")
        start_time = time.time()
        while time.time() - start_time < 5:
            if reader.is_tag_present():
                capabilities['single_tag'] = True
                print("   ✅ Single tag detection works")
                break
            time.sleep(0.1)
        else:
            print("   ❌ Single tag detection failed")
            return capabilities
        
        # Test 2: getNumTags functionality
        print("   Testing getNumTags functionality...")
        max_reported = 0
        measurements = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            num_tags = reader.get_num_tags()
            measurements.append(num_tags)
            if num_tags > max_reported:
                max_reported = num_tags
            time.sleep(0.1)
        
        capabilities['max_simultaneous'] = max_reported
        capabilities['getNumTags_works'] = max_reported > 0
        
        if max_reported >= 2:
            print(f"   ✅ getNumTags reports up to {max_reported} tags simultaneously")
        elif max_reported == 1:
            print("   ⚠️  getNumTags only reports single tags")
        else:
            print("   ❌ getNumTags not working")
        
        # Test 3: selectNextTag functionality
        if max_reported > 1:
            print("   Testing selectNextTag functionality...")
            try:
                success = reader.select_next_tag()
                capabilities['selectNextTag_works'] = success
                if success:
                    print("   ✅ selectNextTag works")
                else:
                    print("   ⚠️  selectNextTag returns false")
            except Exception as e:
                print(f"   ❌ selectNextTag failed: {e}")
        
        return capabilities
    
    @staticmethod
    def simultaneous_detection(reader, min_tags=2, timeout=30):
        """Try true simultaneous multi-tag detection."""
        print(f"🔄 Attempting simultaneous detection of {min_tags}+ tags...")
        print("   Place all tags near the reader at the same time")
        
        start_time = time.time()
        best_result = None
        max_detected = 0
        
        while time.time() - start_time < timeout:
            num_tags = reader.get_num_tags()
            
            if num_tags >= min_tags:
                print(f"   📱 Detected {num_tags} tags simultaneously!")
                
                # Try to read all tags
                try:
                    all_tags = reader.read_all_text()
                    if all_tags and len(all_tags) >= min_tags:
                        print(f"   ✅ Successfully read {len(all_tags)} tags!")
                        return all_tags
                    else:
                        # Get tag info instead
                        all_info = reader.get_all_tags_info()
                        if all_info and len(all_info) >= min_tags:
                            print(f"   ✅ Got info for {len(all_info)} tags!")
                            return all_info
                except Exception as e:
                    print(f"   ⚠️  Error reading multiple tags: {e}")
            
            if num_tags > max_detected:
                max_detected = num_tags
                if num_tags >= min_tags:
                    try:
                        all_info = reader.get_all_tags_info()
                        if all_info:
                            best_result = all_info
                    except:
                        pass
            
            time.sleep(0.2)
        
        if best_result:
            print(f"   ⚠️  Best result: {len(best_result)} tags (not simultaneous)")
            return best_result
        
        print(f"   ❌ Simultaneous detection failed (max seen: {max_detected})")
        return None
    
    @staticmethod
    def rapid_sequential_detection(reader, target_tags=2, timeout=30):
        """Rapid sequential detection - detect tags quickly one after another."""
        print(f"🔄 Rapid sequential detection for {target_tags} tags...")
        print("   Place tags one at a time, quickly:")
        print("   1. Place tag 1, wait for beep/confirmation")
        print("   2. Remove tag 1, place tag 2 immediately")
        print("   3. Continue for more tags...")
        
        detected_tags = []
        seen_uids = set()
        start_time = time.time()
        last_tag_present = False
        detection_window = 2.0  # 2 second window per tag
        last_detection_time = start_time
        
        while time.time() - start_time < timeout and len(detected_tags) < target_tags:
            current_time = time.time()
            is_present = reader.is_tag_present()
            
            # Tag arrival
            if is_present and not last_tag_present:
                print(f"   📱 Tag detected...")
                
                try:
                    # Quick read to identify tag
                    tag_info = reader.get_tag_info()
                    if tag_info:
                        uid = tag_info.get('uid', 'Unknown')
                        
                        if uid not in seen_uids:
                            seen_uids.add(uid)
                            
                            # Try to read text quickly
                            text_data = reader.read_text()
                            tag_data = {**tag_info}
                            if text_data:
                                tag_data.update(text_data)
                            
                            tag_data['detection_order'] = len(detected_tags) + 1
                            tag_data['detection_time'] = current_time - start_time
                            
                            detected_tags.append(tag_data)
                            last_detection_time = current_time
                            
                            tech = tag_info.get('technology_name', 'Unknown')
                            text = text_data.get('text', 'No text') if text_data else 'No text'
                            print(f"   ✅ Tag {len(detected_tags)}: {tech} - '{text}'")
                            print(f"      UID: {uid[:16]}...")
                            
                            if len(detected_tags) < target_tags:
                                print(f"   🔄 Remove this tag and place tag {len(detected_tags)+1}")
                        else:
                            print(f"   🔄 Already seen this tag, try another one")
                
                except Exception as e:
                    print(f"   ⚠️  Error reading tag: {e}")
            
            # Tag departure
            elif not is_present and last_tag_present:
                print(f"   📤 Tag removed")
            
            # Timeout for this detection window
            if current_time - last_detection_time > detection_window and len(detected_tags) > 0:
                remaining = target_tags - len(detected_tags)
                if remaining > 0:
                    print(f"   ⏰ Place next tag ({remaining} remaining)...")
                    last_detection_time = current_time
            
            last_tag_present = is_present
            time.sleep(0.05)  # 50ms polling
        
        if len(detected_tags) >= target_tags:
            print(f"   ✅ Successfully detected {len(detected_tags)} tags sequentially!")
        else:
            print(f"   ⚠️  Only detected {len(detected_tags)} of {target_tags} target tags")
        
        return detected_tags if detected_tags else None
    
    @staticmethod
    def manual_sequential_detection(reader, target_tags=2):
        """Manual sequential detection with user prompts."""
        print(f"🔄 Manual sequential detection for {target_tags} tags...")
        
        detected_tags = []
        seen_uids = set()
        
        for i in range(target_tags):
            print(f"\n--- Tag {i+1} of {target_tags} ---")
            input(f"Place tag {i+1} near the reader and press Enter...")
            
            # Wait for tag detection
            timeout = 10
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if reader.is_tag_present():
                    try:
                        tag_info = reader.get_tag_info()
                        if tag_info:
                            uid = tag_info.get('uid', 'Unknown')
                            
                            if uid not in seen_uids:
                                seen_uids.add(uid)
                                
                                # Read tag data
                                text_data = reader.read_text()
                                tag_data = {**tag_info}
                                if text_data:
                                    tag_data.update(text_data)
                                
                                tag_data['detection_order'] = i + 1
                                detected_tags.append(tag_data)
                                
                                tech = tag_info.get('technology_name', 'Unknown')
                                text = text_data.get('text', 'No text') if text_data else 'No text'
                                print(f"✅ Detected: {tech} - '{text}'")
                                print(f"   UID: {uid[:16]}...")
                                break
                            else:
                                print("🔄 This tag was already detected, try another one")
                    
                    except Exception as e:
                        print(f"⚠️  Error reading tag: {e}")
                
                time.sleep(0.1)
            else:
                print(f"❌ No tag detected within {timeout} seconds")
                continue
            
            if i < target_tags - 1:
                input("Remove the tag and press Enter to continue to the next tag...")
                
                # Wait for tag removal
                while reader.is_tag_present():
                    time.sleep(0.1)
        
        return detected_tags if detected_tags else None

class EnhancedMultiTagDemo:
    def __init__(self):
        self.running = True
        self.strategies = MultiTagStrategies()
        
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"🏷️  {title}")
        print(f"{'='*70}")
    
    def print_tag_summary(self, tags: List[Dict[str, Any]]):
        """Print summary of detected tags."""
        if not tags:
            print("No tags detected")
            return
        
        print(f"\n📊 Detected {len(tags)} tags:")
        print("-" * 50)
        
        for i, tag in enumerate(tags):
            text = tag.get('text', 'No text')
            uid = tag.get('uid', 'Unknown')
            tech = tag.get('technology_name', 'Unknown')
            lang = tag.get('language', 'Unknown')
            order = tag.get('detection_order', i+1)
            
            print(f"Tag {order}:")
            print(f"  Text:       '{text}'")
            print(f"  UID:        {uid}")
            print(f"  Technology: {tech}")
            if lang != 'Unknown':
                print(f"  Language:   {lang}")
            if 'detection_time' in tag:
                print(f"  Detected:   {tag['detection_time']:.1f}s")
            print()
    
    def auto_detect_strategy(self, reader):
        """Automatically detect the best strategy for this hardware."""
        self.print_header("Auto-Detecting Best Strategy")
        
        print("Testing hardware capabilities to determine best approach...")
        capabilities = self.strategies.test_hardware_capabilities(reader)
        
        print(f"\n📋 Hardware Analysis:")
        print(f"   Single tag detection: {'✅' if capabilities['single_tag'] else '❌'}")
        print(f"   getNumTags functional: {'✅' if capabilities['getNumTags_works'] else '❌'}")
        print(f"   Maximum simultaneous: {capabilities['max_simultaneous']}")
        print(f"   selectNextTag works: {'✅' if capabilities['selectNextTag_works'] else '❌'}")
        
        if capabilities['max_simultaneous'] >= 2:
            print(f"\n💡 Recommended strategy: SIMULTANEOUS")
            print(f"   Your hardware supports true multi-tag detection!")
            return 'simultaneous'
        elif capabilities['single_tag']:
            print(f"\n💡 Recommended strategy: RAPID SEQUENTIAL")
            print(f"   Hardware supports single tags - using rapid sequential detection")
            return 'sequential'
        else:
            print(f"\n💡 Recommended strategy: MANUAL SEQUENTIAL")
            print(f"   Basic functionality only - using manual sequential detection")
            return 'manual'
    
    def run_strategy(self, strategy: str, reader, min_tags: int = 2):
        """Run a specific detection strategy."""
        if strategy == 'simultaneous':
            return self.strategies.simultaneous_detection(reader, min_tags)
        elif strategy == 'sequential':
            return self.strategies.rapid_sequential_detection(reader, min_tags)
        elif strategy == 'manual':
            return self.strategies.manual_sequential_detection(reader, min_tags)
        else:
            print(f"❌ Unknown strategy: {strategy}")
            return None
    
    def test_all_strategies(self, reader):
        """Test all available strategies."""
        self.print_header("Testing All Multi-Tag Strategies")
        
        strategies_to_test = [
            ('simultaneous', 'True Simultaneous Detection'),
            ('sequential', 'Rapid Sequential Detection'),
            ('manual', 'Manual Sequential Detection')
        ]
        
        results = {}
        
        for strategy_name, strategy_title in strategies_to_test:
            print(f"\n🧪 Testing: {strategy_title}")
            print("-" * 40)
            
            try:
                tags = self.run_strategy(strategy_name, reader, min_tags=2)
                if tags and len(tags) >= 2:
                    results[strategy_name] = {
                        'success': True,
                        'tags_detected': len(tags),
                        'details': f"Successfully detected {len(tags)} tags"
                    }
                    print(f"✅ {strategy_title}: SUCCESS ({len(tags)} tags)")
                else:
                    results[strategy_name] = {
                        'success': False,
                        'tags_detected': len(tags) if tags else 0,
                        'details': "Failed to detect minimum tags"
                    }
                    print(f"❌ {strategy_title}: FAILED")
            
            except Exception as e:
                results[strategy_name] = {
                    'success': False,
                    'tags_detected': 0,
                    'details': f"Exception: {e}"
                }
                print(f"❌ {strategy_title}: ERROR - {e}")
            
            # Brief pause between tests
            time.sleep(2)
        
        # Summary
        print(f"\n📊 Strategy Test Results:")
        print("=" * 40)
        for strategy, result in results.items():
            status = "PASS" if result['success'] else "FAIL"
            print(f"{strategy:15}: {status:4} - {result['details']}")
        
        # Recommendation
        working_strategies = [s for s, r in results.items() if r['success']]
        if working_strategies:
            best = working_strategies[0]  # Prefer simultaneous if it works
            print(f"\n💡 Recommendation: Use '{best}' strategy")
        else:
            print(f"\n⚠️  No strategies worked reliably")
        
        return results
    
    def run(self, mode: str, strategy: str = 'auto', min_tags: int = 2):
        """Run the enhanced multi-tag demo."""
        print("🏷️  Enhanced Multi-Tag NFC Demo")
        print("=" * 40)
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("⚠️  Warning: This demo typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                if mode == 'auto':
                    # Auto-detect best strategy and use it
                    detected_strategy = self.auto_detect_strategy(reader)
                    print(f"\n🚀 Using detected strategy: {detected_strategy}")
                    tags = self.run_strategy(detected_strategy, reader, min_tags)
                    
                elif mode == 'test':
                    # Test all strategies
                    self.test_all_strategies(reader)
                    return True
                    
                elif mode in ['simultaneous', 'sequential', 'manual']:
                    # Use specific strategy
                    if strategy != 'auto':
                        mode = strategy  # Override with command line strategy
                    
                    self.print_header(f"Multi-Tag Detection: {mode.title()}")
                    tags = self.run_strategy(mode, reader, min_tags)
                    
                else:
                    print(f"❌ Unknown mode: {mode}")
                    return False
                
                # Display results
                if mode != 'test':
                    if tags and len(tags) >= min_tags:
                        self.print_tag_summary(tags)
                        print("✅ Multi-tag detection successful!")
                        return True
                    else:
                        print("❌ Multi-tag detection failed")
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
        
        return True

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Enhanced Multi-Tag NFC Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  auto        Auto-detect best strategy and use it (default)
  simultaneous Try true simultaneous detection
  sequential   Use rapid sequential detection  
  manual       Manual sequential detection
  test         Test all strategies and report capabilities

Strategies:
  auto        Automatically choose best strategy (default)
  force-sim   Force simultaneous detection
  force-seq   Force sequential detection  
  adaptive    Adapt based on hardware

Examples:
  %(prog)s --mode auto                    # Auto-detect and use best strategy
  %(prog)s --mode test                    # Test all strategies
  %(prog)s --mode simultaneous            # Force simultaneous detection
  %(prog)s --mode sequential --min-tags 3 # Sequential detection for 3 tags
        """
    )
    
    parser.add_argument('--mode', default='auto',
                       choices=['auto', 'simultaneous', 'sequential', 'manual', 'test'],
                       help='Detection mode (default: auto)')
    parser.add_argument('--strategy', default='auto',
                       choices=['auto', 'force-sim', 'force-seq', 'adaptive'],
                       help='Detection strategy (default: auto)')
    parser.add_argument('--min-tags', type=int, default=2,
                       help='Minimum number of tags to detect (default: 2)')
    
    args = parser.parse_args()
    
    # Map strategy to mode if needed
    strategy_map = {
        'force-sim': 'simultaneous',
        'force-seq': 'sequential',
        'adaptive': 'auto'
    }
    
    final_strategy = strategy_map.get(args.strategy, args.strategy)
    
    demo = EnhancedMultiTagDemo()
    success = demo.run(args.mode, final_strategy, args.min_tags)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())