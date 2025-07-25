#!/usr/bin/env python3
"""
Multi-Tag NFC Demo

This demo showcases the ability to detect and read from multiple NFC tags simultaneously.
It demonstrates various multi-tag scenarios and provides real-time monitoring.

Usage:
    sudo python multi_tag_demo.py [--mode MODE]

Modes:
    simple      - Simple multi-tag detection
    monitor     - Continuous monitoring for multiple tags
    detailed    - Detailed analysis of each tag
    interactive - Interactive tag selection

Requirements:
    - Root privileges (sudo)
    - Built Python NFC extension with multi-tag support
    - Multiple NFC tags (at least 2 recommended)
    - NFC hardware that supports multi-tag detection

Features:
- Detects multiple NFC tags simultaneously
- Reads text from all tags with NDEF content
- Displays individual tag information (UID, technology, text)
- Real-time monitoring of tag additions/removals
- Interactive tag selection and switching
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

class MultiTagDemo:
    def __init__(self):
        self.running = True
        self.tags_detected = []
        
    def get_timestamp(self):
        """Get formatted timestamp."""
        return datetime.now().strftime("%H:%M:%S")
    
    def print_header(self, title):
        """Print formatted header."""
        print("\n" + "=" * 70)
        print(f"🏷️  {title}")
        print("=" * 70)
    
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
            
            print(f"Tag {i+1}:")
            print(f"  Text:       '{text}'")
            print(f"  UID:        {uid}")
            print(f"  Technology: {tech}")
            print(f"  Language:   {lang}")
            print()
    
    def simple_multi_tag_detection(self):
        """Simple demonstration of multi-tag detection with fallback."""
        self.print_header("Simple Multi-Tag Detection")
        print("This demo will try multiple strategies to detect multiple tags.")
        print("Place 2 or more NFC tags near the reader...")
        print("Waiting for multiple tags (30 second timeout)...")
        
        # First attempt: Standard multi-tag detection
        print("\n🔄 Attempting simultaneous detection...")
        tags = nfc_reader.read_multiple_tags(min_tags=2, timeout=20)
        
        if tags and len(tags) >= 2:
            print(f"\n✅ Success! Found {len(tags)} tags with text content:")
            self.print_tag_summary(tags)
            return True
        
        # Fallback: Check if hardware issue or no tags
        print("\n⚠️  Simultaneous detection failed. Checking hardware...")
        
        with nfc_reader.NFCReader() as reader:
            reader.start_discovery()
            
            # Test basic tag detection
            print("Testing if ANY tags are detected...")
            start_time = time.time()
            any_tag_detected = False
            
            while time.time() - start_time < 5:
                if reader.is_tag_present():
                    any_tag_detected = True
                    num_tags = reader.get_num_tags()
                    print(f"✅ Tag detected! getNumTags() reports: {num_tags}")
                    
                    if num_tags >= 2:
                        print("🎉 Multiple tags detected by getNumTags()!")
                        # Try to read them
                        try:
                            all_tags = reader.read_all_text()
                            if all_tags:
                                print(f"✅ Successfully read {len(all_tags)} tags!")
                                self.print_tag_summary(all_tags)
                                return True
                        except Exception as e:
                            print(f"⚠️  Error reading multiple tags: {e}")
                    break
                time.sleep(0.2)
            
            if not any_tag_detected:
                print("\n❌ No tags detected at all")
                print("\nTroubleshooting:")
                print("1. Make sure NFC tags are close to the reader") 
                print("2. Try with a single tag first to test basic functionality")
                print("3. Check that tags contain NDEF text records")
                return False
            
            # Fallback: Rapid sequential detection
            print("\n🔄 Trying rapid sequential detection...")
            print("Quickly place and remove tags one at a time:")
            
            detected_tags = []
            seen_uids = set()
            start_time = time.time()
            last_tag_present = False
            
            while time.time() - start_time < 20 and len(detected_tags) < 3:
                is_present = reader.is_tag_present()
                
                # Tag arrival
                if is_present and not last_tag_present:
                    try:
                        tag_info = reader.get_tag_info()
                        if tag_info:
                            uid = tag_info.get('uid', 'Unknown')
                            
                            if uid not in seen_uids:
                                seen_uids.add(uid)
                                
                                # Try to read text
                                text_data = reader.read_text()
                                tag_data = {**tag_info}
                                if text_data:
                                    tag_data.update(text_data)
                                
                                detected_tags.append(tag_data)
                                
                                tech = tag_info.get('technology_name', 'Unknown')
                                text = text_data.get('text', 'No text') if text_data else 'No text'
                                print(f"📱 Tag {len(detected_tags)}: {tech} - '{text}'")
                                
                                if len(detected_tags) >= 2:
                                    print(f"\n✅ Sequential detection successful!")
                                    self.print_tag_summary(detected_tags)
                                    return True
                                else:
                                    print(f"   Remove this tag and place another one...")
                    
                    except Exception as e:
                        print(f"⚠️  Error reading tag: {e}")
                
                last_tag_present = is_present
                time.sleep(0.1)
            
            if len(detected_tags) >= 2:
                print(f"\n✅ Sequential detection found {len(detected_tags)} tags!")
                self.print_tag_summary(detected_tags)
                return True
            elif len(detected_tags) == 1:
                print(f"\n⚠️  Only detected 1 tag sequentially")
                print("\nPossible issues:")
                print("1. Your NFC hardware may not support multiple tag detection")
                print("2. Try the enhanced multi-tag demo: nfc_multi_tag_enhanced.py")
                print("3. Use the diagnostic tool: nfc_multi_tag_diagnostic.py")
                return False
            else:
                print("\n❌ No tags detected in sequential mode either")
                print("\nRecommendations:")
                print("1. Test with a single tag first")
                print("2. Run the diagnostic script: sudo python nfc_multi_tag_diagnostic.py")
                print("3. Check NFC hardware compatibility")
                return False
    
    def monitor_multiple_tags(self):
        """Continuous monitoring for multiple tags."""
        self.print_header("Continuous Multi-Tag Monitoring")
        print("This demo continuously monitors for multiple NFC tags.")
        print("Add or remove tags to see real-time updates.")
        print("Press Ctrl+C to stop.\n")
        
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            with nfc_reader.NFCReader() as reader:
                last_count = 0
                last_tags = []
                
                print(f"[{self.get_timestamp()}] 🔍 Starting multi-tag monitor...")
                
                while self.running:
                    current_count = reader.get_num_tags()
                    
                    # Tag count changed
                    if current_count != last_count:
                        if current_count > 0:
                            print(f"[{self.get_timestamp()}] 📱 Detected {current_count} tag(s)")
                            
                            # Get all tag info
                            all_tags = reader.get_all_tags_info()
                            if all_tags:
                                for i, tag in enumerate(all_tags):
                                    uid = tag.get('uid', 'Unknown')[:12] + "..."
                                    tech = tag.get('technology_name', 'Unknown')
                                    print(f"  Tag {i+1}: {tech} (UID: {uid})")
                            
                            # Try to read text from all tags
                            text_tags = reader.read_all_text()
                            if text_tags:
                                print(f"[{self.get_timestamp()}] 📝 Found text in {len(text_tags)} tag(s):")
                                for i, tag in enumerate(text_tags):
                                    text = tag.get('text', 'No text')
                                    lang = tag.get('language', 'Unknown')
                                    print(f"  Tag {i+1}: '{text}' ({lang})")
                            
                            print()
                        else:
                            print(f"[{self.get_timestamp()}] 📤 All tags removed\n")
                        
                        last_count = current_count
                    
                    time.sleep(0.3)  # Check every 300ms
                    
        except KeyboardInterrupt:
            pass
        
        print(f"[{self.get_timestamp()}] 🛑 Monitoring stopped")
    
    def detailed_tag_analysis(self):
        """Detailed analysis of each detected tag."""
        self.print_header("Detailed Multi-Tag Analysis")
        print("Place multiple NFC tags near the reader for detailed analysis...")
        
        with nfc_reader.NFCReader() as reader:
            # Wait for tags
            print("Waiting for tags...")
            start_time = time.time()
            
            while time.time() - start_time < 15:
                num_tags = reader.get_num_tags()
                if num_tags > 0:
                    break
                time.sleep(0.2)
            
            if num_tags == 0:
                print("❌ No tags detected")
                return False
            
            print(f"\n✅ Found {num_tags} tag(s). Analyzing each tag...\n")
            
            # Get detailed info for each tag
            all_tags_info = reader.get_all_tags_info()
            all_tags_text = reader.read_all_text() or []
            
            if all_tags_info:
                for i, tag_info in enumerate(all_tags_info):
                    print(f"🏷️  TAG {i+1} ANALYSIS")
                    print("-" * 30)
                    
                    # Basic info
                    print(f"UID:          {tag_info.get('uid', 'Unknown')}")
                    print(f"Technology:   {tag_info.get('technology_name', 'Unknown')}")
                    print(f"Tech ID:      {tag_info.get('technology', 'Unknown')}")
                    print(f"Handle:       {tag_info.get('handle', 'Unknown')}")
                    print(f"UID Length:   {tag_info.get('uid_length', 0)} bytes")
                    
                    # Find corresponding text data
                    text_data = None
                    for text_tag in all_tags_text:
                        if text_tag.get('uid') == tag_info.get('uid'):
                            text_data = text_tag
                            break
                    
                    if text_data:
                        print(f"Text Content: '{text_data.get('text', 'No text')}'")
                        print(f"Language:     {text_data.get('language', 'Unknown')}")
                        print(f"Record Type:  {text_data.get('type', 'Unknown')}")
                        print("✅ Contains NDEF text record")
                    else:
                        print("Text Content: None")
                        print("❌ No NDEF text record found")
                    
                    print()
            
            return True
    
    def interactive_tag_selection(self):
        """Interactive tag selection and switching."""
        self.print_header("Interactive Multi-Tag Selection")
        print("This demo allows you to interactively switch between detected tags.")
        print("Place multiple NFC tags near the reader...\n")
        
        with nfc_reader.NFCReader() as reader:
            while self.running:
                num_tags = reader.get_num_tags()
                
                if num_tags == 0:
                    print("No tags detected. Place some tags near the reader...")
                    time.sleep(1)
                    continue
                
                print(f"\n🏷️  Found {num_tags} tag(s)")
                
                if num_tags == 1:
                    print("Only one tag detected. Add more tags for multi-selection.")
                    time.sleep(2)
                    continue
                
                # Show all available tags
                all_tags = reader.get_all_tags_info()
                if all_tags:
                    print("\nAvailable tags:")
                    for i, tag in enumerate(all_tags):
                        uid = tag.get('uid', 'Unknown')[:12] + "..."
                        tech = tag.get('technology_name', 'Unknown')
                        print(f"  {i+1}. {tech} (UID: {uid})")
                
                print(f"\nOptions:")
                print("  1-{}: Select specific tag".format(num_tags))
                print("  a: Read all tags")
                print("  q: Quit")
                
                try:
                    choice = input("\nEnter choice: ").strip().lower()
                    
                    if choice == 'q':
                        break
                    elif choice == 'a':
                        text_tags = reader.read_all_text()
                        if text_tags:
                            print(f"\n📝 Text from all {len(text_tags)} tags:")
                            for i, tag in enumerate(text_tags):
                                text = tag.get('text', 'No text')
                                uid = tag.get('uid', 'Unknown')[:8] + "..."
                                print(f"  Tag {i+1}: '{text}' (UID: {uid})")
                        else:
                            print("❌ No text found in any tags")
                    elif choice.isdigit():
                        tag_num = int(choice)
                        if 1 <= tag_num <= num_tags:
                            # Select specific tag (this would require implementing tag selection by index)
                            print(f"🎯 Selected tag {tag_num}")
                            print("Note: Individual tag selection requires additional implementation")
                        else:
                            print(f"❌ Invalid tag number. Choose 1-{num_tags}")
                    else:
                        print("❌ Invalid choice")
                        
                except (ValueError, KeyboardInterrupt):
                    break
                
                time.sleep(0.5)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        self.running = False
    
    def run(self, mode: str):
        """Run the demo in specified mode."""
        print("🏷️  Multi-Tag NFC Demo")
        print("========================")
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("⚠️  Warning: This demo typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        success = False
        
        try:
            if mode == 'simple':
                success = self.simple_multi_tag_detection()
            elif mode == 'monitor':
                self.monitor_multiple_tags()
                success = True
            elif mode == 'detailed':
                success = self.detailed_tag_analysis()
            elif mode == 'interactive':
                self.interactive_tag_selection()
                success = True
            else:
                print(f"❌ Unknown mode: {mode}")
                return False
                
        except nfc_reader.NFCInitializationError as e:
            print(f"\n❌ NFC initialization failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure you're running as root (sudo)")
            print("2. Check that NFC hardware is connected")
            print("3. Ensure no other NFC applications are running")
            return False
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return False
        
        if success:
            print("\n✅ Demo completed successfully!")
        
        return success

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Multi-Tag NFC Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  simple      Simple multi-tag detection (wait for 2+ tags)
  monitor     Continuous monitoring with real-time updates
  detailed    Detailed analysis of each detected tag
  interactive Interactive tag selection and switching

Examples:
  %(prog)s --mode simple      # Wait for multiple tags
  %(prog)s --mode monitor     # Continuous monitoring
  %(prog)s --mode detailed    # Analyze each tag
  %(prog)s --mode interactive # Interactive selection
        """
    )
    
    parser.add_argument('--mode', default='simple',
                       choices=['simple', 'monitor', 'detailed', 'interactive'],
                       help='Demo mode (default: simple)')
    
    args = parser.parse_args()
    
    demo = MultiTagDemo()
    return 0 if demo.run(args.mode) else 1

if __name__ == "__main__":
    sys.exit(main())