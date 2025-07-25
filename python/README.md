# Python NFC Text Reader

This directory contains a Python interface for reading text from NFC tags using the Linux NFC library.

## Overview

The Python interface provides a simple way to:
- Initialize and manage the NFC stack
- Detect NFC tags
- Read NDEF text records
- Write NDEF text records to tags
- Extract text content and language information
- Get detailed tag information
- Work with multiple tags simultaneously

## Files

- `nfc_python_wrapper.c` - C extension that bridges Python and the NFC library
- `setup.py` - Build configuration for the Python extension
- `nfc_reader.py` - High-level Python module with easy-to-use functions
- `example_text_reader.py` - Example script demonstrating various usage patterns
- `nfc_tag_write_demo.py` - Demo script for writing text to NFC tags
- `multi_tag_demo.py` - Demo script for multi-tag detection and reading (with fallback)
- `nfc_monitor_demo.py` - Real-time single tag monitoring demo
- `nfc_multi_monitor_demo.py` - **Real-time multi-tag monitoring with live add/remove detection**
- `build.sh` - Build script to compile the extension
- `README.md` - This file

## Requirements

1. **Linux NFC Library**: The main NFC library must be built first
2. **Python 3.6+**: Python development headers required
3. **Root privileges**: Typically needed for NFC hardware access
4. **NFC Hardware**: Supported NFC reader/writer device

## Building

### 1. Build the main NFC library first

```bash
# From the project root directory
./autogen.sh
./configure
make
```

### 2. Build the Python extension

```bash
cd python

# Option 1: Use the build script
./build.sh

# Option 2: Manual build
python setup.py build_ext --inplace
```

### 3. Install system-wide (optional)

```bash
sudo python setup.py install
```

## Usage

### Simple Text Reading

```python
import nfc_reader

# Read text from an NFC tag (30 second timeout)
text = nfc_reader.read_text_from_tag(timeout=30)
if text:
    print(f"Found text: {text}")
```

### Advanced Usage

```python
import nfc_reader

# Get text with language information
result = nfc_reader.read_text_with_language(timeout=30)
if result:
    print(f"Text: {result['text']}")
    print(f"Language: {result['language']}")

# Get comprehensive tag information
tag_data = nfc_reader.get_tag_data(timeout=30)
if tag_data:
    print(f"UID: {tag_data['uid']}")
    print(f"Technology: {tag_data['technology_name']}")
    print(f"Text: {tag_data.get('text', 'No text found')}")
```

### Writing to NFC Tags

```python
import nfc_reader

# Simple text writing
success = nfc_reader.write_text_to_tag("Hello, World!", "en", timeout=30)
if success:
    print("Text written successfully!")

# Create NDEF record without writing
ndef_data = nfc_reader.create_ndef_text_record("Test message", "en")
if ndef_data:
    print(f"Created NDEF record ({len(ndef_data)} bytes)")
    
    # Write the NDEF data to a tag
    success = nfc_reader.write_ndef_to_tag(ndef_data, timeout=30)
    if success:
        print("NDEF data written successfully!")

# Advanced writing with context manager
with nfc_reader.NFCReader() as reader:
    reader.start_discovery()
    
    # Wait for tag
    print("Place a writable tag near the reader...")
    while not reader.is_tag_present():
        time.sleep(0.1)
    
    # Read current content (for backup)
    current_content = reader.read_text()
    if current_content:
        print(f"Current content: '{current_content['text']}'")
    
    # Write new text
    success = reader.write_text("New content", "en")
    if success:
        print("Text written successfully!")
        
        # Verify by reading back
        verification = reader.read_text()
        if verification and verification['text'] == "New content":
            print("Write verified successfully!")
```

### Multi-Tag Support

```python
import nfc_reader

# Read from multiple tags simultaneously
tags = nfc_reader.read_multiple_tags(min_tags=2, timeout=30)
if tags:
    print(f"Found {len(tags)} tags:")
    for i, tag in enumerate(tags):
        print(f"  Tag {i+1}: '{tag['text']}' (UID: {tag['uid']})")

# Get info for all detected tags
all_tags = nfc_reader.get_all_tag_info(timeout=10)
if all_tags:
    for tag in all_tags:
        print(f"UID: {tag['uid']}, Tech: {tag['technology_name']}")

# Monitor multiple tags continuously
def on_tags_changed(tags):
    print(f"Tags changed: {len(tags)} detected")
    for tag in tags:
        print(f"  {tag.get('text', 'No text')}")

nfc_reader.monitor_multiple_tags(callback=on_tags_changed)
```

### Context Manager (Recommended)

```python
import nfc_reader

# Automatic resource management
with nfc_reader.NFCReader() as reader:
    result = reader.wait_for_tag(timeout=30)
    if result:
        print(f"Text: {result['text']}")
        
    # Check if tag is still present
    if reader.is_tag_present():
        tag_info = reader.get_tag_info()
        print(f"Tag UID: {tag_info['uid']}")

# Multi-tag context manager usage
with nfc_reader.NFCReader() as reader:
    # Wait for multiple tags
    tags = reader.wait_for_multiple_tags(min_tags=2, timeout=30)
    if tags:
        print(f"Found {len(tags)} tags with text")
        
    # Check how many tags are present
    num_tags = reader.get_num_tags()
    print(f"Total tags detected: {num_tags}")
    
    # Get all tag information
    all_tags = reader.get_all_tags_info()
    if all_tags:
        for i, tag in enumerate(all_tags):
            print(f"Tag {i}: {tag['technology_name']}")
```

## Examples

Run the example scripts to see different usage patterns:

### Single Tag Examples

```bash
# Simple text reading
sudo python example_text_reader.py --simple

# Continuous monitoring
sudo python example_text_reader.py --monitor

# Advanced usage with detailed information
sudo python example_text_reader.py --advanced

# Error handling demonstration
sudo python example_text_reader.py --errors
```

### Multi-Tag Examples

```bash
# Simple multi-tag detection (with fallback strategies)
sudo python multi_tag_demo.py --mode simple

# Continuous multi-tag monitoring
sudo python multi_tag_demo.py --mode monitor

# Detailed analysis of each tag
sudo python multi_tag_demo.py --mode detailed

# Interactive tag selection
sudo python multi_tag_demo.py --mode interactive

# Real-time multi-tag monitoring with live updates
sudo python nfc_multi_monitor_demo.py

# Faster refresh rate for real-time monitoring
sudo python nfc_multi_monitor_demo.py --refresh-rate 50
```

### Continuous Monitoring Demo

```bash
# Real-time single tag monitoring with detection/removal events
sudo python nfc_monitor_demo.py

# Simple status mode
sudo python nfc_monitor_demo.py --simple
```

### Tag Writing Demo

```bash
# Simple text writing
sudo python nfc_tag_write_demo.py --mode simple --text "Hello, World!"

# Interactive writing mode
sudo python nfc_tag_write_demo.py --mode interactive

# Batch writing multiple texts
sudo python nfc_tag_write_demo.py --mode batch --text "Text1;Text2;Text3"

# Write with comprehensive verification
sudo python nfc_tag_write_demo.py --mode verify --text "Test message"

# Write in different language
sudo python nfc_tag_write_demo.py --mode simple --text "Bonjour" --language fr

# Force mode (skip confirmations)
sudo python nfc_tag_write_demo.py --mode simple --text "Quick write" --force
```

## API Reference

### High-level Functions

#### Single Tag Functions
- `read_text_from_tag(timeout=30)` - Simple text reading, returns string or None
- `read_text_with_language(timeout=30)` - Returns dict with text and language
- `get_tag_data(timeout=30)` - Returns comprehensive tag information

#### Multi-Tag Functions
- `read_multiple_tags(min_tags=2, timeout=30)` - Read from multiple tags simultaneously
- `get_all_tag_info(timeout=10)` - Get information for all detected tags
- `monitor_multiple_tags(callback=None, min_tags=1)` - Continuous multi-tag monitoring

#### Writing Functions
- `write_text_to_tag(text, language_code="en", timeout=30)` - Simple text writing to tag
- `create_ndef_text_record(text, language_code="en")` - Create NDEF text record
- `write_ndef_to_tag(ndef_data, timeout=30)` - Write pre-created NDEF data to tag

### NFCReader Class

#### Basic Methods
- `NFCReader(auto_cleanup=True)` - Main class for NFC operations
- `initialize()` - Initialize NFC stack
- `cleanup()` - Clean up resources
- `start_discovery()` - Start tag discovery
- `stop_discovery()` - Stop tag discovery

#### Single Tag Methods
- `is_tag_present()` - Check if tag is present
- `read_text()` - Read text from current tag
- `get_tag_info()` - Get tag information
- `wait_for_tag(timeout=30)` - Wait for tag and read text

#### Multi-Tag Methods
- `get_num_tags()` - Get number of detected tags
- `select_next_tag()` - Select next tag in field
- `check_next_protocol()` - Check next valid protocol
- `read_all_text()` - Read text from all detected tags
- `get_all_tags_info()` - Get info for all detected tags
- `wait_for_multiple_tags(min_tags=2, timeout=30)` - Wait for multiple tags

#### Writing Methods
- `create_text_ndef(text, language_code="en")` - Create NDEF text record
- `write_ndef(ndef_data)` - Write NDEF data to current tag
- `write_text(text, language_code="en")` - Write text to current tag

### Low-level Functions

- `initialize()` - Initialize NFC stack
- `deinitialize()` - Deinitialize NFC stack
- `start_discovery()` - Start discovery
- `stop_discovery()` - Stop discovery

## Error Handling

The module defines several exception types:

- `NFCError` - Base exception for NFC errors
- `NFCInitializationError` - NFC initialization failed

Always handle these exceptions in your code:

```python
try:
    with nfc_reader.NFCReader() as reader:
        result = reader.wait_for_tag(timeout=30)
        # Process result
except nfc_reader.NFCInitializationError as e:
    print(f"NFC init failed: {e}")
except nfc_reader.NFCError as e:
    print(f"NFC error: {e}")
```

## Troubleshooting

### Permission Errors

```bash
# Run with root privileges
sudo python example_text_reader.py

# Or add user to dialout group (may not work for all hardware)
sudo usermod -a -G dialout $USER
```

### Build Errors

```bash
# Install Python development headers
sudo apt install python3-dev

# Check that the main library was built
ls -la ../.libs/libnfc_nci_linux.so
# or
ls -la ../libnfc_nci_linux.so
```

### Runtime Errors

1. **"nfc_native module not found"**
   - Build the extension: `python setup.py build_ext --inplace`

2. **"NFC initialization failed"**
   - Check hardware connection
   - Run as root
   - Ensure no other NFC applications are running

3. **"No text found"**
   - Ensure the NFC tag contains NDEF text records
   - Try with a known working tag (like one written by an Android phone)
   - Check that the tag is close enough to the reader

4. **"Failed to write text to tag"**
   - Ensure the tag is writable (not read-only)
   - Check that the tag supports NDEF format
   - Some tags need to be formatted before first use
   - Verify tag is close enough to the reader
   - Try writing shorter text content

5. **Multi-tag detection not working**
   - Check if getNumTags() returns values > 1 with debug logging enabled
   - For PN7160 controllers: Use `sudo python nfc_multi_monitor_demo.py` for real-time monitoring
   - Multi-tag works best with sequential access using selectNextTag()
   - Try the real-time monitor to see live multi-tag detection

### Writing Safety

When writing to NFC tags:

1. **Always backup existing content** - The demos automatically read current content before writing
2. **Use confirmation prompts** - All demos include safety confirmations unless `--force` is used
3. **Verify writes** - Check that written content matches expected content
4. **Handle write-protected tags** - Some tags may be locked or read-only
5. **Test with disposable tags** - Use test tags when developing to avoid losing important data

## Supported Tag Types

The interface currently supports:
- NDEF Text records (TNF Well-Known Type, RTD Text)
- Various NFC tag technologies (Type A, Type B, Type F, etc.)
- Mifare Classic, Mifare Ultralight
- ISO14443-4 tags

## Multi-Tag Support

This library provides comprehensive multi-tag detection capabilities using hardware anti-collision:

### Real-Time Multi-Tag Monitoring
The `nfc_multi_monitor_demo.py` tool provides live monitoring of multiple tags:

- **Live tag list**: See all tags currently in range with real-time updates
- **Add/remove detection**: Instant notification when tags enter or leave the field
- **Tag details**: UID, technology, text content, and timing information
- **Session statistics**: Track total tags detected and peak simultaneous count

### How Multi-Tag Detection Works
- Uses `getNumTags()` to determine total tags in range
- Uses `selectNextTag()` to cycle through detected tags sequentially
- Hardware anti-collision enables detection of multiple UIDs
- Sequential access provides complete tag information for each detected tag

### Usage Recommendations

1. **For real-time monitoring**: Use `nfc_multi_monitor_demo.py` for live tag tracking
2. **For batch collection**: Use `multi_tag_demo.py` for collecting multiple tag data
3. **For single tag apps**: Use `example_text_reader.py` or `nfc_monitor_demo.py`

## Performance Notes

- Tag detection typically takes 100-500ms
- Text reading adds another 100-200ms
- Use appropriate timeouts to balance responsiveness and battery life
- The `check_interval` parameter in `wait_for_tag()` controls polling frequency

## License

This Python interface follows the same Apache 2.0 license as the main project.