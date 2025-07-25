#!/usr/bin/env python3
"""
Continuous NFC Tag Monitor Demo

This demo continuously monitors for NFC tags and displays real-time status
including tag detection, text content, and removal events.

Usage:
    sudo python nfc_monitor_demo.py

Features:
- Real-time tag detection and removal monitoring
- Clean status display with timestamps
- Text extraction from NDEF records
- Tag information display (UID, technology)
- Persistent monitoring until interrupted

Requirements:
- Root privileges (sudo)
- Built Python NFC extension
- NFC hardware connected
"""

import sys
import time
import signal
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import nfc_reader
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

class NFCMonitor:
    def __init__(self):
        self.running = True
        self.tag_count = 0
        self.current_tag_data = None
        self.reader = None
        
    def get_timestamp(self):
        """Get formatted timestamp for display."""
        return datetime.now().strftime("%H:%M:%S")
    
    def print_status(self, message, prefix="INFO"):
        """Print status message with timestamp."""
        timestamp = self.get_timestamp()
        print(f"[{timestamp}] {prefix}: {message}")
    
    def print_tag_info(self, tag_data):
        """Display detailed tag information."""
        text = tag_data.get('text', 'No text')
        language = tag_data.get('language', 'Unknown')
        uid = tag_data.get('uid', 'Unknown')
        tech = tag_data.get('technology_name', 'Unknown')
        
        print("─" * 60)
        print(f"[{self.get_timestamp()}] 📱 TAG DETECTED #{self.tag_count}")
        print(f"  Text Content: '{text}'")
        print(f"  Language:     {language}")
        print(f"  UID:          {uid}")
        print(f"  Technology:   {tech}")
        print("─" * 60)
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print(f"\n[{self.get_timestamp()}] 🛑 Shutting down monitor...")
        self.running = False
    
    def monitor_tags(self):
        """Main monitoring loop."""
        print("=" * 60)
        print("🔍 NFC TAG MONITOR - Continuous Mode")
        print("=" * 60)
        print("Place NFC tags near the reader to see real-time detection")
        print("Press Ctrl+C to stop monitoring")
        print("=" * 60)
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        
        try:
            # Initialize NFC reader
            self.reader = nfc_reader.NFCReader()
            self.reader.initialize()
            self.reader.start_discovery()
            
            self.print_status("NFC reader initialized and discovery started")
            self.print_status("Waiting for NFC tags...")
            
            last_tag_present = False
            
            while self.running:
                try:
                    # Check if tag is present
                    tag_present = self.reader.is_tag_present()
                    
                    # Tag just arrived
                    if tag_present and not last_tag_present:
                        self.tag_count += 1
                        
                        # Read tag data
                        text_data = self.reader.read_text()
                        tag_info = self.reader.get_tag_info()
                        
                        # Combine data
                        combined_data = {}
                        if text_data:
                            combined_data.update(text_data)
                        if tag_info:
                            combined_data.update(tag_info)
                        
                        self.current_tag_data = combined_data
                        self.print_tag_info(combined_data)
                        
                        last_tag_present = True
                    
                    # Tag just removed
                    elif not tag_present and last_tag_present:
                        if self.current_tag_data:
                            tag_text = self.current_tag_data.get('text', 'Unknown')
                            tag_uid = self.current_tag_data.get('uid', 'Unknown')[:8] + "..."
                        else:
                            tag_text = "Unknown"
                            tag_uid = "Unknown"
                        
                        print(f"[{self.get_timestamp()}] 📤 TAG REMOVED")
                        print(f"  Last text: '{tag_text}' (UID: {tag_uid})")
                        print()
                        
                        self.current_tag_data = None
                        last_tag_present = False
                        
                        self.print_status("Ready for next tag...")
                    
                    # Small delay to prevent excessive polling
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.print_status(f"Error during monitoring: {e}", "ERROR")
                    time.sleep(1)
            
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
            
        finally:
            # Cleanup
            if self.reader:
                try:
                    self.reader.cleanup()
                    self.print_status("NFC reader cleaned up")
                except Exception as e:
                    self.print_status(f"Cleanup error: {e}", "ERROR")
        
        return True
    
    def run(self):
        """Run the monitor and display summary."""
        success = self.monitor_tags()
        
        print("\n" + "=" * 60)
        print("📊 MONITORING SUMMARY")
        print("=" * 60)
        print(f"Total tags processed: {self.tag_count}")
        print(f"Session duration: Started at {self.get_timestamp()}")
        
        if success:
            print("✅ Monitor completed successfully")
        else:
            print("❌ Monitor completed with errors")
        
        print("=" * 60)

def show_simple_status():
    """Alternative simple status display mode."""
    print("🔍 Simple NFC Monitor")
    print("Place tags near reader, remove to see status changes")
    print("Press Ctrl+C to stop")
    print("-" * 40)
    
    try:
        with nfc_reader.NFCReader() as reader:
            last_present = False
            tag_count = 0
            
            while True:
                present = reader.is_tag_present()
                
                if present and not last_present:
                    tag_count += 1
                    text_data = reader.read_text()
                    text = text_data.get('text', 'No text') if text_data else 'No text'
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Tag #{tag_count}: '{text}'")
                    last_present = True
                    
                elif not present and last_present:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Tag removed")
                    last_present = False
                
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print(f"\nStopped. Total tags: {tag_count}")

def main():
    """Main function with mode selection."""
    import os
    
    # Check if running as root
    if os.geteuid() != 0:
        print("⚠️  Warning: This script typically requires root privileges.")
        print("If you encounter errors, try running with 'sudo'")
        print()
    
    # Simple argument parsing
    if len(sys.argv) > 1 and sys.argv[1] == '--simple':
        show_simple_status()
    else:
        monitor = NFCMonitor()
        monitor.run()

if __name__ == "__main__":
    main()