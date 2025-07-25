#!/usr/bin/env python3
"""
Example script demonstrating how to read text from NFC tags using the Python interface.

This script shows various ways to interact with NFC tags and extract text content.
It includes examples of simple text reading, continuous monitoring, and error handling.

Usage:
    python example_text_reader.py [--simple|--monitor|--advanced]

Requirements:
    - Root privileges (sudo)
    - Built Python NFC extension
    - NFC hardware connected and configured

Examples:
    # Simple one-time text reading
    sudo python example_text_reader.py --simple
    
    # Continuous monitoring for tags
    sudo python example_text_reader.py --monitor
    
    # Advanced usage with detailed tag information
    sudo python example_text_reader.py --advanced
"""

import sys
import time
import argparse
import logging
from typing import Optional, Dict, Any

try:
    import nfc_reader
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python")
    print("  python setup.py build_ext --inplace")
    sys.exit(1)

def simple_text_reading():
    """Simple example: read text from one NFC tag."""
    print("=== Simple Text Reading ===")
    print("Place an NFC tag with text near the reader...")
    print("Waiting for tag (30 second timeout)...")
    
    text = nfc_reader.read_text_from_tag(timeout=30)
    
    if text:
        print(f"\n✓ Success! Found text: '{text}'")
        return True
    else:
        print("\n✗ No text found or timeout reached")
        return False

def advanced_text_reading():
    """Advanced example: read text with language and tag information."""
    print("\n=== Advanced Text Reading ===")
    print("This example shows detailed tag information including text and metadata.")
    print("Place an NFC tag near the reader...")
    
    # Read text with language information
    result = nfc_reader.read_text_with_language(timeout=30)
    
    if result:
        print(f"\n✓ Text found:")
        print(f"  Content: '{result['text']}'")
        print(f"  Language: {result['language']}")
        print(f"  Type: {result['type']}")
        
        # Get additional tag information
        print("\nGetting detailed tag information...")
        tag_data = nfc_reader.get_tag_data(timeout=5)  # Should be quick since tag is already detected
        
        if tag_data:
            print(f"\n✓ Tag details:")
            print(f"  UID: {tag_data.get('uid', 'Unknown')}")
            print(f"  Technology: {tag_data.get('technology_name', 'Unknown')}")
            print(f"  Technology ID: {tag_data.get('technology', 'Unknown')}")
            print(f"  Handle: {tag_data.get('handle', 'Unknown')}")
            print(f"  UID Length: {tag_data.get('uid_length', 0)} bytes")
        
        return True
    else:
        print("\n✗ No text found or timeout reached")
        return False

def continuous_monitoring():
    """Continuous monitoring example: keep reading tags until interrupted."""
    print("\n=== Continuous Monitoring ===")
    print("This example continuously monitors for NFC tags.")
    print("Press Ctrl+C to stop.")
    print()
    
    try:
        with nfc_reader.NFCReader() as reader:
            tag_count = 0
            
            while True:
                print(f"Waiting for tag #{tag_count + 1}...")
                
                result = reader.wait_for_tag(timeout=60)  # Wait up to 1 minute
                
                if result:
                    tag_count += 1
                    print(f"\n✓ Tag #{tag_count} detected!")
                    print(f"  Text: '{result['text']}'")
                    print(f"  Language: {result['language']}")
                    
                    # Get tag info
                    tag_info = reader.get_tag_info()
                    if tag_info:
                        print(f"  UID: {tag_info.get('uid', 'Unknown')}")
                        print(f"  Technology: {tag_info.get('technology_name', 'Unknown')}")
                    
                    print("\nWaiting for tag to be removed...")
                    
                    # Wait for tag to be removed
                    while reader.is_tag_present():
                        time.sleep(0.2)
                    
                    print("Tag removed.\n")
                    time.sleep(1)  # Brief pause before next detection
                else:
                    print("Timeout waiting for tag. Continuing...")
                    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        print(f"Total tags processed: {tag_count}")

def test_error_handling():
    """Demonstrate error handling and edge cases."""
    print("\n=== Error Handling Demo ===")
    
    # Test without initialization
    print("Testing error handling...")
    
    try:
        # This should handle the case gracefully
        reader = nfc_reader.NFCReader(auto_cleanup=False)
        
        # Try to read without initialization
        result = reader.read_text()
        print(f"Read without init result: {result}")
        
        # Now initialize properly
        print("Initializing NFC...")
        reader.initialize()
        
        # Test reading with no tag present
        print("Testing read with no tag present...")
        result = reader.read_text()
        print(f"No tag result: {result}")
        
        # Cleanup
        reader.cleanup()
        print("Error handling test completed successfully.")
        
    except nfc_reader.NFCError as e:
        print(f"NFC Error (expected): {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def main():
    """Main function with command line argument handling."""
    parser = argparse.ArgumentParser(
        description="NFC Text Reader Examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --simple     Read text from one tag
  %(prog)s --monitor    Continuously monitor for tags
  %(prog)s --advanced   Show detailed tag information
  %(prog)s --errors     Demonstrate error handling
        """
    )
    
    parser.add_argument('--simple', action='store_true',
                       help='Simple one-time text reading')
    parser.add_argument('--monitor', action='store_true',
                       help='Continuous monitoring for tags')
    parser.add_argument('--advanced', action='store_true',
                       help='Advanced reading with detailed information')
    parser.add_argument('--errors', action='store_true',
                       help='Demonstrate error handling')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)
    
    # Check if running as root
    import os
    if os.geteuid() != 0:
        print("Warning: This script typically requires root privileges to access NFC hardware.")
        print("If you encounter permission errors, try running with 'sudo'.")
        print()
    
    print("NFC Text Reader Examples")
    print("========================")
    print()
    
    try:
        success = False
        
        if args.simple:
            success = simple_text_reading()
        elif args.monitor:
            continuous_monitoring()
            success = True
        elif args.advanced:
            success = advanced_text_reading()
        elif args.errors:
            test_error_handling()
            success = True
        else:
            # Default: run simple example
            print("No specific mode selected, running simple example.")
            print("Use --help to see available options.")
            print()
            success = simple_text_reading()
        
        if success:
            print("\n✓ Example completed successfully!")
        else:
            print("\n✗ Example completed but no text was found.")
            
    except nfc_reader.NFCInitializationError as e:
        print(f"\n✗ NFC initialization failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're running as root (sudo)")
        print("2. Check that NFC hardware is connected")
        print("3. Ensure the NFC library was built correctly")
        print("4. Check that no other NFC applications are running")
        return 1
        
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
        return 0
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())