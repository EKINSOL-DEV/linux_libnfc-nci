#!/usr/bin/env python3
"""
Simple Multi-Tag Detection for Limited Hardware

This script provides a practical multi-tag solution for NFC hardware
that doesn't support getNumTags() properly (like yours).

It uses a simple, reliable approach:
1. Detect when a tag is present
2. Read it quickly
3. Ask user to replace with next tag
4. Repeat until done

Usage:
    sudo python nfc_simple_multi_tag.py [--tags N]
"""

import sys
import time
import argparse
from datetime import datetime

try:
    import nfc_reader
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

def simple_multi_tag_collection(num_tags=3):
    """
    Simple, user-guided multi-tag data collection.
    
    This approach works reliably with any NFC hardware because it:
    1. Only uses is_tag_present() and basic read functions
    2. Doesn't rely on broken getNumTags() API
    3. Uses clear user prompts for tag replacement
    """
    print(f"📱 Simple Multi-Tag Data Collection")
    print("=" * 50)
    print(f"Collecting data from {num_tags} different NFC tags...")
    print("This method works with ANY NFC hardware.\n")
    
    collected_tags = []
    
    try:
        with nfc_reader.NFCReader() as reader:
            reader.start_discovery()
            
            for i in range(num_tags):
                print(f"\n--- TAG {i+1} of {num_tags} ---")
                
                if i == 0:
                    input("Place the FIRST NFC tag near the reader and press Enter...")
                else:
                    input(f"Replace with tag {i+1} and press Enter...")
                
                print("Reading tag...")
                
                # Wait for tag detection
                timeout = 10
                start_time = time.time()
                tag_detected = False
                
                while time.time() - start_time < timeout:
                    if reader.is_tag_present():
                        tag_detected = True
                        break
                    time.sleep(0.1)
                
                if not tag_detected:
                    print(f"❌ No tag detected within {timeout} seconds")
                    print("Skipping this tag...")
                    continue
                
                # Read tag data
                try:
                    tag_info = reader.get_tag_info()
                    text_data = reader.read_text()
                    
                    if not tag_info:
                        print("⚠️  Could not read tag info")
                        continue
                    
                    # Combine data
                    tag_data = {
                        'tag_number': i + 1,
                        'timestamp': datetime.now().isoformat(),
                        **tag_info
                    }
                    
                    if text_data:
                        tag_data.update(text_data)
                    
                    collected_tags.append(tag_data)
                    
                    # Display results
                    uid = tag_info.get('uid', 'Unknown')
                    tech = tag_info.get('technology_name', 'Unknown')
                    text = text_data.get('text', 'No text') if text_data else 'No text'
                    
                    print(f"✅ Tag {i+1} read successfully!")
                    print(f"   Technology: {tech}")
                    print(f"   UID: {uid}")
                    print(f"   Text: '{text}'")
                    
                except Exception as e:
                    print(f"❌ Error reading tag {i+1}: {e}")
                    continue
                
                # Wait for tag removal (except for last tag)
                if i < num_tags - 1:
                    print(f"\nRemove tag {i+1} before placing tag {i+2}...")
                    while reader.is_tag_present():
                        time.sleep(0.2)
                    print("✅ Tag removed")
                    time.sleep(0.5)  # Brief pause
        
        # Summary
        print(f"\n📊 COLLECTION COMPLETE")
        print("=" * 50)
        print(f"Successfully collected data from {len(collected_tags)} tags:")
        
        for tag in collected_tags:
            num = tag.get('tag_number', '?')
            tech = tag.get('technology_name', 'Unknown')
            text = tag.get('text', 'No text')
            uid = tag.get('uid', 'Unknown')[:16]
            
            print(f"\nTag {num}: {tech}")
            print(f"  Text: '{text}'")
            print(f"  UID: {uid}...")
        
        if len(collected_tags) >= num_tags:
            print(f"\n🎉 SUCCESS: Collected all {num_tags} target tags!")
            return True
        else:
            print(f"\n⚠️  Partial success: {len(collected_tags)} of {num_tags} tags collected")
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

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Simple Multi-Tag NFC Data Collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool provides reliable multi-tag data collection for NFC hardware
that doesn't support advanced multi-tag APIs (like getNumTags()).

It uses a simple, user-guided approach that works with any NFC hardware.

Examples:
  %(prog)s --tags 3    # Collect data from 3 different tags
  %(prog)s --tags 5    # Collect data from 5 different tags
        """
    )
    
    parser.add_argument('--tags', type=int, default=3,
                       help='Number of tags to collect data from (default: 3)')
    
    args = parser.parse_args()
    
    if args.tags < 1:
        print("❌ Number of tags must be at least 1")
        return 1
    
    # Check permissions
    import os
    if os.geteuid() != 0:
        print("⚠️  Warning: This tool typically requires root privileges.")
        print("If you encounter errors, try running with 'sudo'\n")
    
    success = simple_multi_tag_collection(args.tags)
    
    if success:
        print("\n✅ Multi-tag data collection completed successfully!")
        print("\n💡 This approach works reliably with your NFC hardware")
        print("   because it doesn't rely on the broken getNumTags() API.")
    else:
        print("\n⚠️  Multi-tag collection completed with issues")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())