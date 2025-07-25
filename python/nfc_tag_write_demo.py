#!/usr/bin/env python3
"""
NFC Tag Writing Demo

This demo showcases the ability to write text content to NFC tags.
It provides multiple writing modes and safety features to prevent accidental overwrites.

Usage:
    sudo python nfc_tag_write_demo.py [options]

Options:
    --text TEXT         Text to write to the tag
    --language LANG     Language code (default: en)
    --mode MODE         Demo mode: simple, interactive, batch, or verify
    --timeout SECONDS   Timeout for tag detection (default: 30)
    --force             Skip confirmation prompts

Requirements:
    - Root privileges (sudo)
    - Built Python NFC extension with writing support
    - Writable NFC tags (NDEF compatible)
    - NFC hardware that supports writing

Safety Features:
- Confirmation prompts before writing
- Tag content verification after writing
- Backup of original content (when possible)
- Support for different tag types

Writing Modes:
- simple:      Write predefined text to a tag
- interactive: Interactive text input and tag selection
- batch:       Write multiple texts to multiple tags
- verify:      Write and verify tag content
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

class NFCWriteDemo:
    def __init__(self):
        self.running = True
        self.written_tags = []
        
    def get_timestamp(self):
        """Get formatted timestamp."""
        return datetime.now().strftime("%H:%M:%S")
    
    def print_header(self, title):
        """Print formatted header."""
        print("\n" + "=" * 70)
        print(f"✍️  {title}")
        print("=" * 70)
    
    def print_warning(self, message):
        """Print warning message."""
        print(f"\n⚠️  WARNING: {message}")
    
    def print_success(self, message):
        """Print success message."""
        print(f"\n✅ SUCCESS: {message}")
    
    def print_error(self, message):
        """Print error message."""
        print(f"\n❌ ERROR: {message}")
    
    def confirm_action(self, message, force=False):
        """Get user confirmation for an action."""
        if force:
            return True
        
        try:
            response = input(f"\n{message} (y/N): ").strip().lower()
            return response in ['y', 'yes']
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return False
    
    def read_current_tag_content(self, reader):
        """Read current content of a tag for backup purposes."""
        try:
            current_content = reader.read_text()
            if current_content:
                return current_content.get('text', ''), current_content.get('language', 'unknown')
            return None, None
        except Exception as e:
            print(f"Could not read current tag content: {e}")
            return None, None
    
    def verify_written_content(self, reader, expected_text, expected_language="en"):
        """Verify that the written content matches what was intended."""
        try:
            # Small delay to allow tag to be written
            time.sleep(0.5)
            
            result = reader.read_text()
            if result:
                written_text = result.get('text', '')
                written_language = result.get('language', '')
                
                if written_text == expected_text and written_language == expected_language:
                    return True, written_text, written_language
                else:
                    return False, written_text, written_language
            return False, None, None
        except Exception as e:
            print(f"Verification failed: {e}")
            return False, None, None
    
    def simple_write_demo(self, text, language_code="en", timeout=30, force=False):
        """Simple demonstration of writing text to an NFC tag."""
        self.print_header("Simple Text Writing")
        print(f"Text to write: '{text}'")
        print(f"Language: {language_code}")
        print(f"Timeout: {timeout} seconds")
        
        if not self.confirm_action(f"Write '{text}' to the next NFC tag?", force):
            return False
        
        print(f"\nPlace a writable NFC tag near the reader...")
        print("Waiting for tag...")
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if reader.is_tag_present():
                        print(f"\n[{self.get_timestamp()}] 📱 Tag detected!")
                        
                        # Get tag info
                        tag_info = reader.get_tag_info()
                        if tag_info:
                            print(f"Tag Type: {tag_info.get('technology_name', 'Unknown')}")
                            print(f"Tag UID: {tag_info.get('uid', 'Unknown')}")
                        
                        # Read current content for backup
                        current_text, current_lang = self.read_current_tag_content(reader)
                        if current_text:
                            print(f"Current content: '{current_text}' ({current_lang})")
                            if not self.confirm_action("Overwrite existing content?", force):
                                return False
                        
                        # Write the text
                        print(f"\n[{self.get_timestamp()}] ✍️  Writing text...")
                        success = reader.write_text(text, language_code)
                        
                        if success:
                            self.print_success(f"Text written successfully!")
                            
                            # Verify the content
                            print("Verifying written content...")
                            verified, written_text, written_lang = self.verify_written_content(reader, text, language_code)
                            
                            if verified:
                                self.print_success(f"Verification passed: '{written_text}' ({written_lang})")
                                self.written_tags.append({
                                    'uid': tag_info.get('uid', 'Unknown') if tag_info else 'Unknown',
                                    'text': text,
                                    'language': language_code,
                                    'timestamp': self.get_timestamp(),
                                    'original_text': current_text,
                                    'original_language': current_lang
                                })
                                return True
                            else:
                                self.print_error(f"Verification failed! Expected: '{text}', Got: '{written_text}'")
                                return False
                        else:
                            self.print_error("Failed to write text to tag")
                            return False
                    
                    time.sleep(0.1)
                
                self.print_error("Timeout waiting for tag")
                return False
                
        except nfc_reader.NFCInitializationError as e:
            self.print_error(f"NFC initialization failed: {e}")
            return False
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            return False
    
    def interactive_write_demo(self, timeout=30):
        """Interactive writing demo with user input."""
        self.print_header("Interactive Text Writing")
        print("This mode allows you to interactively write text to NFC tags.")
        print("You can write multiple different texts to multiple tags.")
        print("Press Ctrl+C to stop.\n")
        
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                while self.running:
                    # Get text input from user
                    try:
                        text = input("\nEnter text to write (or 'quit' to exit): ").strip()
                        if text.lower() in ['quit', 'exit', 'q']:
                            break
                        
                        if not text:
                            print("Please enter some text to write.")
                            continue
                        
                        language = input("Enter language code (default: en): ").strip() or "en"
                        
                        print(f"\nReady to write: '{text}' ({language})")
                        print("Place a writable NFC tag near the reader...")
                        
                        # Wait for tag
                        tag_found = False
                        start_time = time.time()
                        
                        while time.time() - start_time < timeout and self.running:
                            if reader.is_tag_present():
                                tag_found = True
                                break
                            time.sleep(0.1)
                        
                        if not tag_found:
                            print("❌ Timeout waiting for tag. Try again.")
                            continue
                        
                        print(f"\n[{self.get_timestamp()}] 📱 Tag detected!")
                        
                        # Get tag info
                        tag_info = reader.get_tag_info()
                        if tag_info:
                            print(f"Tag Type: {tag_info.get('technology_name', 'Unknown')}")
                            print(f"Tag UID: {tag_info.get('uid', 'Unknown')}")
                        
                        # Read current content
                        current_text, current_lang = self.read_current_tag_content(reader)
                        if current_text:
                            print(f"Current content: '{current_text}' ({current_lang})")
                            if not self.confirm_action("Overwrite existing content?"):
                                continue
                        
                        # Confirm write
                        if not self.confirm_action(f"Write '{text}' to this tag?"):
                            continue
                        
                        # Write the text
                        print(f"\n[{self.get_timestamp()}] ✍️  Writing text...")
                        success = reader.write_text(text, language)
                        
                        if success:
                            self.print_success("Text written successfully!")
                            
                            # Verify
                            verified, written_text, written_lang = self.verify_written_content(reader, text, language)
                            if verified:
                                self.print_success(f"Verification passed: '{written_text}' ({written_lang})")
                                self.written_tags.append({
                                    'uid': tag_info.get('uid', 'Unknown') if tag_info else 'Unknown',
                                    'text': text,
                                    'language': language,
                                    'timestamp': self.get_timestamp(),
                                    'original_text': current_text,
                                    'original_language': current_lang
                                })
                            else:
                                self.print_error(f"Verification failed!")
                        else:
                            self.print_error("Failed to write text")
                        
                        print("\nRemove the tag and place a new one for the next write, or enter new text.")
                        
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        self.print_error(f"Error: {e}")
                        
        except Exception as e:
            self.print_error(f"Demo error: {e}")
        
        print(f"\n[{self.get_timestamp()}] 🛑 Interactive demo stopped")
    
    def batch_write_demo(self, text_list, language_code="en", timeout=30, force=False):
        """Write multiple texts to multiple tags in sequence."""
        self.print_header("Batch Text Writing")
        print(f"Texts to write: {len(text_list)} items")
        for i, text in enumerate(text_list):
            print(f"  {i+1}. '{text}'")
        print(f"Language: {language_code}")
        
        if not self.confirm_action(f"Write {len(text_list)} texts to {len(text_list)} tags?", force):
            return False
        
        successful_writes = 0
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                for i, text in enumerate(text_list):
                    if not self.running:
                        break
                    
                    print(f"\n{'='*50}")
                    print(f"Writing {i+1}/{len(text_list)}: '{text}'")
                    print(f"{'='*50}")
                    print("Place next NFC tag near the reader...")
                    
                    # Wait for tag
                    tag_found = False
                    start_time = time.time()
                    
                    while time.time() - start_time < timeout and self.running:
                        if reader.is_tag_present():
                            tag_found = True
                            break
                        time.sleep(0.1)
                    
                    if not tag_found:
                        self.print_error(f"Timeout waiting for tag {i+1}. Skipping...")
                        continue
                    
                    print(f"\n[{self.get_timestamp()}] 📱 Tag {i+1} detected!")
                    
                    # Get tag info
                    tag_info = reader.get_tag_info()
                    if tag_info:
                        print(f"Tag Type: {tag_info.get('technology_name', 'Unknown')}")
                        print(f"Tag UID: {tag_info.get('uid', 'Unknown')}")
                    
                    # Check for existing content
                    current_text, current_lang = self.read_current_tag_content(reader)
                    if current_text and not force:
                        print(f"Current content: '{current_text}' ({current_lang})")
                        if not self.confirm_action(f"Overwrite with '{text}'?"):
                            print("Skipping this tag...")
                            continue
                    
                    # Write the text
                    print(f"\n[{self.get_timestamp()}] ✍️  Writing '{text}'...")
                    success = reader.write_text(text, language_code)
                    
                    if success:
                        # Verify
                        verified, written_text, written_lang = self.verify_written_content(reader, text, language_code)
                        if verified:
                            self.print_success(f"Tag {i+1} written and verified!")
                            successful_writes += 1
                            self.written_tags.append({
                                'uid': tag_info.get('uid', 'Unknown') if tag_info else 'Unknown',
                                'text': text,
                                'language': language_code,
                                'timestamp': self.get_timestamp(),
                                'batch_index': i+1,
                                'original_text': current_text,
                                'original_language': current_lang
                            })
                        else:
                            self.print_error(f"Tag {i+1} write failed verification!")
                    else:
                        self.print_error(f"Failed to write to tag {i+1}")
                    
                    if i < len(text_list) - 1:
                        print("\nRemove current tag and place the next one...")
                        # Wait for tag removal
                        while reader.is_tag_present() and self.running:
                            time.sleep(0.1)
                        time.sleep(0.5)  # Brief pause
                
        except Exception as e:
            self.print_error(f"Batch demo error: {e}")
        
        print(f"\n📊 Batch writing complete: {successful_writes}/{len(text_list)} successful")
        return successful_writes == len(text_list)
    
    def verify_write_demo(self, text, language_code="en", timeout=30, force=False):
        """Write text and perform comprehensive verification."""
        self.print_header("Write with Verification")
        print(f"Text to write: '{text}'")
        print(f"Language: {language_code}")
        print("This mode includes comprehensive verification of the write operation.")
        
        if not self.confirm_action(f"Write and verify '{text}'?", force):
            return False
        
        print(f"\nPlace a writable NFC tag near the reader...")
        
        try:
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if reader.is_tag_present():
                        print(f"\n[{self.get_timestamp()}] 📱 Tag detected!")
                        
                        # Step 1: Get tag information
                        tag_info = reader.get_tag_info()
                        if tag_info:
                            print(f"✓ Tag Type: {tag_info.get('technology_name', 'Unknown')}")
                            print(f"✓ Tag UID: {tag_info.get('uid', 'Unknown')}")
                        
                        # Step 2: Read original content
                        print("\n🔍 Reading original content...")
                        original_text, original_lang = self.read_current_tag_content(reader)
                        if original_text:
                            print(f"✓ Original content: '{original_text}' ({original_lang})")
                        else:
                            print("✓ Tag appears to be empty or unformatted")
                        
                        # Step 3: Create NDEF record
                        print(f"\n🔧 Creating NDEF record...")
                        ndef_data = reader.create_text_ndef(text, language_code)
                        if ndef_data:
                            print(f"✓ NDEF record created ({len(ndef_data)} bytes)")
                        else:
                            self.print_error("Failed to create NDEF record")
                            return False
                        
                        # Step 4: Write to tag
                        print(f"\n✍️  Writing to tag...")
                        write_success = reader.write_ndef(ndef_data)
                        if write_success:
                            print("✓ Write operation completed")
                        else:
                            self.print_error("Write operation failed")
                            return False
                        
                        # Step 5: Verify by reading back
                        print(f"\n🔍 Verifying written content...")
                        time.sleep(0.5)  # Allow time for write to complete
                        
                        verified, read_text, read_lang = self.verify_written_content(reader, text, language_code)
                        if verified:
                            print(f"✅ Verification PASSED!")
                            print(f"✓ Read back: '{read_text}' ({read_lang})")
                            print(f"✓ Matches expected: '{text}' ({language_code})")
                        else:
                            self.print_error("Verification FAILED!")
                            print(f"✗ Expected: '{text}' ({language_code})")
                            print(f"✗ Got: '{read_text}' ({read_lang})")
                            return False
                        
                        # Step 6: Record the operation
                        self.written_tags.append({
                            'uid': tag_info.get('uid', 'Unknown') if tag_info else 'Unknown',
                            'text': text,
                            'language': language_code,
                            'timestamp': self.get_timestamp(),
                            'ndef_size': len(ndef_data),
                            'verified': True,
                            'original_text': original_text,
                            'original_language': original_lang
                        })
                        
                        self.print_success("Write and verification completed successfully!")
                        return True
                    
                    time.sleep(0.1)
                
                self.print_error("Timeout waiting for tag")
                return False
                
        except Exception as e:
            self.print_error(f"Verification demo error: {e}")
            return False
    
    def print_summary(self):
        """Print summary of all write operations."""
        if not self.written_tags:
            print("\nNo tags were written during this session.")
            return
        
        print(f"\n📋 WRITE SUMMARY")
        print("=" * 50)
        print(f"Total tags written: {len(self.written_tags)}")
        
        for i, tag in enumerate(self.written_tags):
            print(f"\nTag {i+1}:")
            print(f"  UID: {tag['uid']}")
            print(f"  Written: '{tag['text']}' ({tag['language']})")
            print(f"  Time: {tag['timestamp']}")
            if tag.get('original_text'):
                print(f"  Previous: '{tag['original_text']}' ({tag['original_language']})")
            if tag.get('batch_index'):
                print(f"  Batch: {tag['batch_index']}")
            if tag.get('ndef_size'):
                print(f"  NDEF size: {tag['ndef_size']} bytes")
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        self.running = False
    
    def run(self, mode: str, text: str = None, language: str = "en", timeout: float = 30, force: bool = False):
        """Run the demo in specified mode."""
        print("✍️  NFC Tag Writing Demo")
        print("=" * 30)
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("⚠️  Warning: This demo typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        success = False
        
        try:
            if mode == 'simple':
                if not text:
                    text = input("Enter text to write: ").strip()
                    if not text:
                        self.print_error("No text provided")
                        return False
                success = self.simple_write_demo(text, language, timeout, force)
                
            elif mode == 'interactive':
                self.interactive_write_demo(timeout)
                success = True
                
            elif mode == 'batch':
                if not text:
                    print("Enter texts to write (one per line, empty line to finish):")
                    text_list = []
                    while True:
                        line = input(f"Text {len(text_list)+1}: ").strip()
                        if not line:
                            break
                        text_list.append(line)
                else:
                    # Split text on semicolons for batch mode
                    text_list = [t.strip() for t in text.split(';') if t.strip()]
                
                if not text_list:
                    self.print_error("No texts provided")
                    return False
                
                success = self.batch_write_demo(text_list, language, timeout, force)
                
            elif mode == 'verify':
                if not text:
                    text = input("Enter text to write and verify: ").strip()
                    if not text:
                        self.print_error("No text provided")
                        return False
                success = self.verify_write_demo(text, language, timeout, force)
                
            else:
                self.print_error(f"Unknown mode: {mode}")
                return False
                
        except nfc_reader.NFCInitializationError as e:
            self.print_error(f"NFC initialization failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure you're running as root (sudo)")
            print("2. Check that NFC hardware is connected")
            print("3. Ensure no other NFC applications are running")
            return False
            
        except KeyboardInterrupt:
            print(f"\n[{self.get_timestamp()}] 🛑 Demo interrupted by user")
            
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            return False
        
        finally:
            self.print_summary()
        
        if success:
            print("\n✅ Demo completed successfully!")
        
        return success

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="NFC Tag Writing Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  simple      Write a single text to one tag
  interactive Interactive mode for writing multiple texts
  batch       Write multiple texts to multiple tags in sequence
  verify      Write with comprehensive verification

Examples:
  %(prog)s --mode simple --text "Hello, World!"
  %(prog)s --mode interactive
  %(prog)s --mode batch --text "Text1;Text2;Text3"
  %(prog)s --mode verify --text "Test message" --language en
  %(prog)s --mode simple --text "Bonjour" --language fr --force
        """
    )
    
    parser.add_argument('--mode', default='simple',
                       choices=['simple', 'interactive', 'batch', 'verify'],
                       help='Demo mode (default: simple)')
    parser.add_argument('--text',
                       help='Text to write (use semicolons to separate multiple texts for batch mode)')
    parser.add_argument('--language', default='en',
                       help='Language code (default: en)')
    parser.add_argument('--timeout', type=float, default=30.0,
                       help='Timeout for tag detection in seconds (default: 30)')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    demo = NFCWriteDemo()
    return 0 if demo.run(args.mode, args.text, args.language, args.timeout, args.force) else 1

if __name__ == "__main__":
    sys.exit(main())