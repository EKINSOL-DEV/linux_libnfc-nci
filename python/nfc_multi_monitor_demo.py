#!/usr/bin/env python3
"""
Real-Time Multi-Tag NFC Monitor

This tool provides live monitoring of multiple NFC tags in range, updating
the display in real-time as tags are added or removed. It leverages the
PN7160's working multi-tag detection using selectNextTag() and getNumTags().

The monitor shows:
- Live count of tags in range
- Real-time list of detected tags with details
- Add/remove events with timestamps
- Tag information: UID, technology, text content

Based on confirmed working PN7160 multi-tag detection that uses anti-collision
and selectNextTag() to access multiple tags sequentially.

Usage:
    sudo python nfc_multi_monitor_demo.py [--refresh-rate MS]
"""

import sys
import time
import signal
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Set

try:
    import nfc_reader
    import nfc_native  # Still needed for selectNextTag
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

class MultiTagMonitor:
    """Real-time monitor for multiple NFC tags using PN7160 capabilities."""
    
    def __init__(self, refresh_rate_ms=100):
        self.running = True
        self.refresh_rate = refresh_rate_ms / 1000.0  # Convert to seconds
        self.current_tags = {}  # UID -> tag data mapping
        self.tag_order = []     # Track order of tag detection
        self.total_detected = 0
        self.session_start = datetime.now()
        
        # Display state
        self.last_display_lines = 0
        
        # Setup signal handler for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        self.running = False
        print("\n\n🛑 Shutting down monitor...")
    
    def clear_display(self):
        """Clear the current display."""
        if self.last_display_lines > 0:
            # Move cursor up and clear lines
            for _ in range(self.last_display_lines):
                print("\033[A\033[K", end="")
        self.last_display_lines = 0
    
    def display_status(self):
        """Display current multi-tag status."""
        lines = []
        
        # Header
        runtime = datetime.now() - self.session_start
        runtime_str = f"{int(runtime.total_seconds())}s"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        lines.append("=" * 70)
        lines.append(f"🔍 Multi-Tag NFC Monitor - {timestamp} (Running: {runtime_str})")
        lines.append("=" * 70)
        
        # Current status
        num_tags = len(self.current_tags)
        if num_tags == 0:
            lines.append("📱 No tags in range")
            lines.append("   Place NFC tags near the reader to monitor them...")
        else:
            lines.append(f"📱 {num_tags} tag{'s' if num_tags != 1 else ''} in range:")
            
            # Display each tag
            for i, uid in enumerate(self.tag_order):
                if uid in self.current_tags:
                    tag_data = self.current_tags[uid]
                    
                    # Tag header
                    tech = tag_data.get('technology_name', 'Unknown')
                    detection_time = tag_data.get('first_seen', 'Unknown')
                    
                    lines.append(f"")
                    lines.append(f"   🏷️  Tag {i+1}: {tech}")
                    lines.append(f"       UID: {uid}")
                    lines.append(f"       First seen: {detection_time}")
                    
                    # Text content
                    text = tag_data.get('text', 'No text')
                    if text and text != 'No text':
                        lines.append(f"       Text: '{text}'")
                    else:
                        lines.append(f"       Text: No NDEF text found")
                    
                    # Additional info
                    handle = tag_data.get('handle', 'Unknown')
                    lines.append(f"       Handle: {handle}")
                    
                    last_seen = tag_data.get('last_seen', 'Unknown')
                    lines.append(f"       Last seen: {last_seen}")
        
        # Session statistics
        lines.append("")
        lines.append(f"📊 Session Stats:")
        lines.append(f"   Total tags detected: {self.total_detected}")
        lines.append(f"   Currently in range: {num_tags}")
        lines.append(f"   Refresh rate: {int(self.refresh_rate * 1000)}ms")
        
        lines.append("")
        lines.append("💡 Tip: Add/remove tags to see real-time updates")
        lines.append("   Press Ctrl+C to stop monitoring")
        
        # Display all lines
        for line in lines:
            print(line)
        
        self.last_display_lines = len(lines)
    
    def scan_tags(self, reader):
        """Scan for all tags currently in range using the reader instance."""
        current_scan = {}
        
        try:
            # Start with a direct discovery check - don't rely on is_tag_present() alone
            # as it may be too restrictive for multi-tag scenarios
            reader.start_discovery()  # Ensure discovery is active
            
            # Get total count first - this is the primary indicator
            num_tags = reader.get_num_tags()
            
            # If no tags according to count, double-check with is_tag_present
            if num_tags <= 0:
                is_present = reader.is_tag_present()
                if not is_present:
                    return current_scan
                # If present but count is 0, treat as 1 tag (fallback for single tag)
                num_tags = 1
            
            # Read all tags using selectNextTag cycling
            # First, read the current tag (tag index 0)
            try:
                tag_info = reader.get_tag_info()
                
                if tag_info and isinstance(tag_info, dict):
                    uid = tag_info.get('uid', 'Unknown')
                    
                    if uid != 'Unknown':
                        # Create tag data entry
                        tag_data = {
                            'uid': uid,
                            'technology_name': tag_info.get('technology_name', 'Unknown'),
                            'handle': tag_info.get('handle', 'Unknown'),
                            'last_seen': datetime.now().strftime("%H:%M:%S.%f")[:-3],
                            'tag_index': 0
                        }
                        
                        # Try to read text content
                        try:
                            text_data = reader.read_text()
                            if text_data and text_data.get('text'):
                                tag_data['text'] = text_data['text']
                                tag_data['language'] = text_data.get('language', 'unknown')
                            else:
                                tag_data['text'] = 'No text'
                        except:
                            tag_data['text'] = 'Read error'
                        
                        current_scan[uid] = tag_data
                    
            except:
                pass
            
            # If there are multiple tags, try to get the others
            if num_tags > 1:
                for tag_index in range(1, num_tags):
                    try:
                        # Switch to next tag
                        switch_result = nfc_native.select_next_tag()
                        
                        if switch_result:
                            time.sleep(0.05)  # Pause for tag switch
                            
                            # Get next tag info
                            tag_info = reader.get_tag_info()
                            
                            if tag_info and isinstance(tag_info, dict):
                                uid = tag_info.get('uid', 'Unknown')
                                
                                if uid != 'Unknown' and uid not in current_scan:
                                    # Create tag data entry
                                    tag_data = {
                                        'uid': uid,
                                        'technology_name': tag_info.get('technology_name', 'Unknown'),
                                        'handle': tag_info.get('handle', 'Unknown'),
                                        'last_seen': datetime.now().strftime("%H:%M:%S.%f")[:-3],
                                        'tag_index': tag_index
                                    }
                                    
                                    # Try to read text content
                                    try:
                                        text_data = reader.read_text()
                                        if text_data and text_data.get('text'):
                                            tag_data['text'] = text_data['text']
                                            tag_data['language'] = text_data.get('language', 'unknown')
                                        else:
                                            tag_data['text'] = 'No text'
                                    except:
                                        tag_data['text'] = 'Read error'
                                    
                                    current_scan[uid] = tag_data
                    
                    except:
                        continue
        
        except Exception as e:
            # Return empty scan on critical error
            return {}
        
        return current_scan
    
    def update_tag_list(self, scanned_tags):
        """Update the current tag list based on scan results."""
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Find new tags (added)
        for uid, tag_data in scanned_tags.items():
            if uid not in self.current_tags:
                # New tag detected
                tag_data['first_seen'] = current_time
                self.current_tags[uid] = tag_data
                self.tag_order.append(uid)
                self.total_detected += 1
                
                # Log addition (will be visible briefly before next display update)
                tech = tag_data.get('technology_name', 'Unknown')
                print(f"\n[{current_time}] ➕ Tag added: {uid[:16]}... ({tech})")
            else:
                # Update existing tag data
                existing = self.current_tags[uid]
                existing.update(tag_data)
                existing['first_seen'] = existing.get('first_seen', current_time)  # Preserve original time
        
        # Find removed tags
        removed_uids = []
        for uid in list(self.current_tags.keys()):
            if uid not in scanned_tags:
                removed_uids.append(uid)
        
        # Remove tags that are no longer present
        for uid in removed_uids:
            if uid in self.current_tags:
                tag_data = self.current_tags[uid]
                tech = tag_data.get('technology_name', 'Unknown')
                print(f"\n[{current_time}] ➖ Tag removed: {uid[:16]}... ({tech})")
                
                del self.current_tags[uid]
                if uid in self.tag_order:
                    self.tag_order.remove(uid)
    
    def run(self):
        """Run the multi-tag monitor."""
        print("🔍 Real-Time Multi-Tag NFC Monitor")
        print("=" * 40)
        print("This monitor shows live updates as tags are added and removed.")
        print("Place multiple NFC tags near the reader to see them appear.")
        print("\nInitializing NFC...")
        
        try:
            # Use NFCReader context manager like the working tests
            with nfc_reader.NFCReader() as reader:
                reader.start_discovery()
                
                print("✅ NFC initialized and discovery started")
                print(f"🔄 Refresh rate: {int(self.refresh_rate * 1000)}ms")
                
                print("\n" * 3)  # Initial spacing for display
                
                # Main monitoring loop
                scan_error_count = 0
                while self.running:
                    try:
                        # Scan for current tags using the reader
                        scanned_tags = self.scan_tags(reader)
                        scan_error_count = 0  # Reset error counter on successful scan
                        
                        # Update tag list and detect changes
                        self.update_tag_list(scanned_tags)
                        
                        # Clear previous display and show current status
                        self.clear_display()
                        self.display_status()
                        
                        # Wait before next refresh
                        time.sleep(self.refresh_rate)
                    
                    except KeyboardInterrupt:
                        # Handled by signal handler
                        break
                    except Exception as e:
                        scan_error_count += 1
                        print(f"\n❌ Monitor error #{scan_error_count}: {e}")
                        
                        # If we have many consecutive errors, try restarting discovery
                        if scan_error_count >= 5:
                            print(f"\n🔄 Too many scan errors, restarting discovery...")
                            try:
                                reader.stop_discovery()
                                time.sleep(0.1)
                                reader.start_discovery()
                                scan_error_count = 0
                                print(f"✅ Discovery restarted")
                            except Exception as restart_error:
                                print(f"❌ Failed to restart discovery: {restart_error}")
                        
                        time.sleep(self.refresh_rate * 2)  # Longer pause on error
                
                return True
        
        except nfc_reader.NFCInitializationError as e:
            print(f"❌ NFC initialization failed: {e}")
            print("Make sure you're running as root and NFC hardware is connected")
            return False
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            return False
        
        finally:
            # Final summary
            print(f"\n📊 Final Session Summary:")
            print(f"   Total tags detected: {self.total_detected}")
            print(f"   Session duration: {datetime.now() - self.session_start}")
            print(f"   Peak tags simultaneously: {len(self.current_tags)}")

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Real-Time Multi-Tag NFC Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This monitor provides live updates of NFC tags in range, showing real-time
additions and removals. It uses the PN7160's working multi-tag detection
capabilities with selectNextTag() and getNumTags().

Features:
• Live tag count and details
• Real-time add/remove detection  
• Tag information: UID, technology, text content
• Session statistics and timing
• Clean terminal display with live updates

The monitor leverages confirmed working PN7160 multi-tag detection using
anti-collision and sequential tag access.

Examples:
  %(prog)s                           # Standard 100ms refresh
  %(prog)s --refresh-rate 50         # Faster 50ms refresh
  %(prog)s --refresh-rate 200        # Slower 200ms refresh
        """
    )
    
    parser.add_argument('--refresh-rate', type=int, default=100, metavar='MS',
                       help='Display refresh rate in milliseconds (default: 100)')
    
    args = parser.parse_args()
    
    if args.refresh_rate < 10:
        print("❌ Refresh rate must be at least 10ms")
        return 1
    
    if args.refresh_rate > 5000:
        print("❌ Refresh rate must be less than 5000ms")
        return 1
    
    # Check permissions
    import os
    if os.geteuid() != 0:
        print("⚠️  Warning: This monitor typically requires root privileges.")
        print("If you encounter errors, try running with 'sudo'\n")
    
    # Run monitor
    monitor = MultiTagMonitor(refresh_rate_ms=args.refresh_rate)
    success = monitor.run()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())