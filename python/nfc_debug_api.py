#!/usr/bin/env python3
"""
NFC API Debug Tool

This tool directly tests the low-level NFC API functions to understand
why getNumTags() is returning 0 even when tags are present.
"""

import sys
import time

try:
    import nfc_reader
    import nfc_native
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

def main():
    print("🔍 NFC API Debug Tool")
    print("=" * 40)
    
    print("Initializing NFC...")
    try:
        success = nfc_native.initialize()
        if not success:
            print("❌ NFC initialization failed")
            return 1
        print("✅ NFC initialized")
    except Exception as e:
        print(f"❌ NFC initialization error: {e}")
        return 1
    
    print("\nStarting discovery...")
    try:
        nfc_native.start_discovery()
        print("✅ Discovery started")
    except Exception as e:
        print(f"❌ Discovery start error: {e}")
        return 1
    
    print("\n📱 Place a single NFC tag near the reader...")
    print("Monitoring API calls for 20 seconds...\n")
    
    start_time = time.time()
    last_present = None
    last_num_tags = None
    
    while time.time() - start_time < 20:
        try:
            # Test basic presence
            is_present = nfc_native.is_tag_present()
            num_tags = nfc_native.get_num_tags()
            
            # Only print when values change
            if is_present != last_present or num_tags != last_num_tags:
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] is_present={is_present}, getNumTags()={num_tags}")
                
                if is_present:
                    # Try to get tag info
                    try:
                        tag_info = nfc_native.get_tag_info()
                        if tag_info:
                            uid = tag_info.get('uid', 'Unknown')[:16]
                            tech = tag_info.get('technology_name', 'Unknown')
                            handle = tag_info.get('handle', 'Unknown')
                            print(f"         Tag info: {tech} (UID: {uid}..., Handle: {handle})")
                        else:
                            print(f"         Tag info: None")
                    except Exception as e:
                        print(f"         Tag info error: {e}")
                    
                    # Test selectNextTag
                    try:
                        next_result = nfc_native.select_next_tag()
                        print(f"         selectNextTag(): {next_result}")
                    except Exception as e:
                        print(f"         selectNextTag() error: {e}")
                    
                    # Test checkNextProtocol
                    try:
                        protocol = nfc_native.check_next_protocol()
                        print(f"         checkNextProtocol(): {protocol}")
                    except Exception as e:
                        print(f"         checkNextProtocol() error: {e}")
                
                last_present = is_present
                last_num_tags = num_tags
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
            time.sleep(0.5)
    
    print(f"\n🧪 Analysis:")
    if last_present and last_num_tags == 0:
        print("❌ ISSUE FOUND: is_tag_present() works but getNumTags() always returns 0")
        print("   This indicates getNumTags() is not implemented correctly")
        print("   or there's a configuration issue with the NFC stack")
        print("\n💡 Possible causes:")
        print("   1. getNumTags() API not supported by this NFC hardware")
        print("   2. Multi-tag functionality not enabled in NFC configuration")
        print("   3. Bug in the getNumTags() implementation")
        print("   4. Discovery mode not configured for multi-tag support")
    elif not last_present:
        print("❌ No tags detected at all")
        print("   Check tag placement and hardware connection")
    elif last_num_tags > 0:
        print(f"✅ getNumTags() working correctly (returned {last_num_tags})")
    else:
        print("⚠️  Inconclusive results")
    
    # Cleanup
    try:
        nfc_native.stop_discovery()
        nfc_native.deinitialize()
        print("\n✅ Cleanup completed")
    except Exception as e:
        print(f"\n⚠️  Cleanup error: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())