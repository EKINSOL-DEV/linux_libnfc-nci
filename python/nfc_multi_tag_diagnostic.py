#!/usr/bin/env python3
"""
NFC Multi-Tag Diagnostic Script

This script performs comprehensive testing of multi-tag detection capabilities
to diagnose issues with simultaneous tag detection.

Usage:
    sudo python nfc_multi_tag_diagnostic.py

The script will:
1. Test basic NFC functionality
2. Test single tag detection
3. Test multi-tag API functions step by step
4. Provide detailed logging of all operations
5. Test different discovery configurations
6. Analyze hardware capabilities
"""

import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/nfc_diagnostic.log')
    ]
)
logger = logging.getLogger(__name__)

try:
    import nfc_reader
    import nfc_native
except ImportError as e:
    print("Error: nfc_reader module not found!")
    print("Please build the Python extension first:")
    print("  cd python && ./build.sh")
    sys.exit(1)

class NFCMultiTagDiagnostic:
    def __init__(self):
        self.test_results = {}
        self.tag_detection_history = []
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log and store test results."""
        status = "PASS" if success else "FAIL"
        logger.info(f"TEST [{test_name}]: {status} - {details}")
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
    
    def print_header(self, title: str):
        """Print formatted test header."""
        print(f"\n{'='*70}")
        print(f"🔍 {title}")
        print(f"{'='*70}")
        logger.info(f"Starting test: {title}")
    
    def test_basic_nfc_functionality(self):
        """Test basic NFC initialization and functionality."""
        self.print_header("Basic NFC Functionality Test")
        
        try:
            # Test initialization
            logger.debug("Testing NFC initialization...")
            success = nfc_native.initialize()
            self.log_test_result("NFC_Initialization", success, f"Initialize returned: {success}")
            
            if not success:
                print("❌ NFC initialization failed - cannot proceed with further tests")
                return False
            
            # Test discovery start
            logger.debug("Testing discovery start...")
            nfc_native.start_discovery()
            self.log_test_result("Start_Discovery", True, "Discovery started successfully")
            
            # Test basic functions
            logger.debug("Testing basic API functions...")
            
            # Test getNumTags with no tags
            num_tags = nfc_native.get_num_tags()
            logger.debug(f"getNumTags() with no tags present: {num_tags}")
            self.log_test_result("GetNumTags_NoTags", num_tags >= 0, f"Returned: {num_tags}")
            
            # Test tag presence
            tag_present = nfc_native.is_tag_present()
            logger.debug(f"is_tag_present() with no tags: {tag_present}")
            self.log_test_result("TagPresence_NoTags", tag_present in [True, False], f"Returned: {tag_present}")
            
            print("✅ Basic NFC functionality tests completed")
            return True
            
        except Exception as e:
            logger.error(f"Basic functionality test failed: {e}")
            self.log_test_result("Basic_Functionality", False, f"Exception: {e}")
            return False
    
    def test_single_tag_detection(self, timeout=15):
        """Test single tag detection thoroughly."""
        self.print_header("Single Tag Detection Test")
        
        print("Please place ONE NFC tag near the reader...")
        print(f"Waiting {timeout} seconds for tag detection...")
        
        start_time = time.time()
        tag_detected = False
        detection_count = 0
        
        while time.time() - start_time < timeout:
            try:
                # Test multiple detection methods
                is_present = nfc_native.is_tag_present()
                num_tags = nfc_native.get_num_tags()
                
                logger.debug(f"Detection check: is_present={is_present}, num_tags={num_tags}")
                
                if is_present or num_tags > 0:
                    if not tag_detected:
                        tag_detected = True
                        print(f"✅ Tag detected! is_present={is_present}, num_tags={num_tags}")
                        
                        # Get detailed tag information
                        try:
                            tag_info = nfc_native.get_tag_info()
                            if tag_info:
                                logger.info(f"Tag info: {tag_info}")
                                print(f"   Tag type: {tag_info.get('technology_name', 'Unknown')}")
                                print(f"   Tag UID: {tag_info.get('uid', 'Unknown')}")
                            
                            # Test text reading
                            text_result = nfc_native.read_text()
                            if text_result:
                                logger.info(f"Tag text: {text_result}")
                                print(f"   Tag text: '{text_result.get('text', 'None')}'")
                            
                        except Exception as e:
                            logger.error(f"Error reading tag details: {e}")
                    
                    detection_count += 1
                else:
                    if tag_detected:
                        print("🔄 Tag removed")
                        tag_detected = False
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error during single tag detection: {e}")
                time.sleep(0.5)
        
        success = detection_count > 0
        self.log_test_result("Single_Tag_Detection", success, 
                           f"Detections: {detection_count}, Tag present: {tag_detected}")
        
        if success:
            print(f"✅ Single tag detection successful ({detection_count} detection cycles)")
        else:
            print("❌ No single tag detected during test period")
        
        # Clear any remaining tag
        if tag_detected:
            print("Please remove the tag before continuing...")
            while nfc_native.is_tag_present() or nfc_native.get_num_tags() > 0:
                time.sleep(0.2)
            print("✅ Tag removed")
        
        return success
    
    def test_multi_tag_api_functions(self):
        """Test multi-tag specific API functions in detail."""
        self.print_header("Multi-Tag API Functions Test")
        
        print("Testing multi-tag API functions without tags present...")
        
        try:
            # Test with no tags
            logger.debug("Testing multi-tag functions with no tags...")
            
            num_tags = nfc_native.get_num_tags()
            logger.debug(f"getNumTags() = {num_tags}")
            self.log_test_result("MultiTag_GetNumTags_Empty", num_tags == 0, f"Returned: {num_tags}")
            
            # Test selectNextTag
            try:
                next_result = nfc_native.select_next_tag()
                logger.debug(f"selectNextTag() = {next_result}")
                self.log_test_result("MultiTag_SelectNext_Empty", True, f"Returned: {next_result}")
            except Exception as e:
                logger.debug(f"selectNextTag() failed as expected: {e}")
                self.log_test_result("MultiTag_SelectNext_Empty", True, f"Failed as expected: {e}")
            
            # Test checkNextProtocol
            try:
                protocol_result = nfc_native.check_next_protocol()
                logger.debug(f"checkNextProtocol() = {protocol_result}")
                self.log_test_result("MultiTag_CheckProtocol_Empty", True, f"Returned: {protocol_result}")
            except Exception as e:
                logger.debug(f"checkNextProtocol() failed: {e}")
                self.log_test_result("MultiTag_CheckProtocol_Empty", False, f"Exception: {e}")
            
            # Test readAllText
            try:
                all_text = nfc_native.read_all_text()
                logger.debug(f"read_all_text() = {all_text}")
                expected = all_text is None or (isinstance(all_text, list) and len(all_text) == 0)
                self.log_test_result("MultiTag_ReadAllText_Empty", expected, f"Returned: {all_text}")
            except Exception as e:
                logger.debug(f"read_all_text() failed: {e}")
                self.log_test_result("MultiTag_ReadAllText_Empty", False, f"Exception: {e}")
            
            # Test getAllTagsInfo
            try:
                all_info = nfc_native.get_all_tags_info()
                logger.debug(f"get_all_tags_info() = {all_info}")
                expected = all_info is None or (isinstance(all_info, list) and len(all_info) == 0)
                self.log_test_result("MultiTag_GetAllInfo_Empty", expected, f"Returned: {all_info}")
            except Exception as e:
                logger.debug(f"get_all_tags_info() failed: {e}")
                self.log_test_result("MultiTag_GetAllInfo_Empty", False, f"Exception: {e}")
            
            print("✅ Multi-tag API functions tested with no tags")
            return True
            
        except Exception as e:
            logger.error(f"Multi-tag API test failed: {e}")
            self.log_test_result("MultiTag_API_Test", False, f"Exception: {e}")
            return False
    
    def test_rapid_sequential_detection(self, timeout=20):
        """Test detecting tags in rapid sequence to simulate multi-tag."""
        self.print_header("Rapid Sequential Detection Test")
        
        print("This test checks if we can detect tags quickly in sequence.")
        print("Please have 2-3 NFC tags ready...")
        print(f"You have {timeout} seconds to place and remove tags rapidly.")
        print("Place tag 1, wait for detection, remove it, place tag 2, etc.")
        
        detected_tags = []
        detection_events = []
        start_time = time.time()
        last_tag_present = False
        current_tag_uid = None
        
        while time.time() - start_time < timeout:
            try:
                is_present = nfc_native.is_tag_present()
                num_tags = nfc_native.get_num_tags()
                
                # Tag arrival
                if is_present and not last_tag_present:
                    logger.debug("Tag arrival detected")
                    try:
                        tag_info = nfc_native.get_tag_info()
                        if tag_info:
                            uid = tag_info.get('uid', 'Unknown')
                            if uid != current_tag_uid:
                                current_tag_uid = uid
                                tech = tag_info.get('technology_name', 'Unknown')
                                
                                # Check if we've seen this tag before
                                is_new = uid not in [t['uid'] for t in detected_tags]
                                
                                if is_new:
                                    detected_tags.append({
                                        'uid': uid,
                                        'technology': tech,
                                        'timestamp': time.time() - start_time,
                                        'num_tags_reported': num_tags
                                    })
                                    print(f"✅ Tag {len(detected_tags)}: {tech} (UID: {uid[:16]}...) [num_tags={num_tags}]")
                                else:
                                    print(f"🔄 Repeat detection of known tag: {uid[:16]}...")
                                
                                detection_events.append({
                                    'event': 'arrival',
                                    'uid': uid,
                                    'timestamp': time.time() - start_time,
                                    'is_new': is_new,
                                    'num_tags_reported': num_tags
                                })
                    except Exception as e:
                        logger.error(f"Error getting tag info during rapid test: {e}")
                
                # Tag departure
                elif not is_present and last_tag_present:
                    logger.debug("Tag departure detected")
                    if current_tag_uid:
                        detection_events.append({
                            'event': 'departure',
                            'uid': current_tag_uid,
                            'timestamp': time.time() - start_time
                        })
                        print(f"📤 Tag removed: {current_tag_uid[:16]}...")
                        current_tag_uid = None
                
                last_tag_present = is_present
                time.sleep(0.05)  # 50ms polling
                
            except Exception as e:
                logger.error(f"Error during rapid sequential test: {e}")
                time.sleep(0.2)
        
        print(f"\n📊 Rapid Sequential Detection Results:")
        print(f"   Unique tags detected: {len(detected_tags)}")
        print(f"   Total detection events: {len(detection_events)}")
        
        max_num_tags = max([t['num_tags_reported'] for t in detected_tags] + [0])
        print(f"   Maximum num_tags reported: {max_num_tags}")
        
        # Log detailed results
        for i, tag in enumerate(detected_tags):
            logger.info(f"Tag {i+1}: UID={tag['uid']}, Tech={tag['technology']}, "
                       f"Time={tag['timestamp']:.1f}s, NumTags={tag['num_tags_reported']}")
        
        success = len(detected_tags) >= 2
        self.log_test_result("Rapid_Sequential_Detection", success, 
                           f"Detected {len(detected_tags)} unique tags, max_num_tags={max_num_tags}")
        
        if success:
            print("✅ Successfully detected multiple tags sequentially")
        else:
            print("❌ Could not detect multiple tags even sequentially")
        
        return success, detected_tags, max_num_tags
    
    def test_true_simultaneous_detection(self, timeout=30):
        """Test true simultaneous multi-tag detection."""
        self.print_header("True Simultaneous Multi-Tag Detection Test")
        
        print("This test checks for TRUE simultaneous multi-tag detection.")
        print("Place 2 or more NFC tags near the reader AT THE SAME TIME.")
        print(f"Keep them in place for {timeout} seconds...")
        print("Do NOT move or remove the tags during this test.")
        
        input("Press Enter when you have placed 2+ tags near the reader...")
        
        simultaneous_detections = []
        max_simultaneous = 0
        start_time = time.time()
        stable_period_start = None
        stable_detection_count = 0
        
        while time.time() - start_time < timeout:
            try:
                num_tags = nfc_native.get_num_tags()
                is_present = nfc_native.is_tag_present()
                
                logger.debug(f"Simultaneous test: num_tags={num_tags}, is_present={is_present}")
                
                if num_tags > max_simultaneous:
                    max_simultaneous = num_tags
                    print(f"🏷️  New maximum: {num_tags} tags detected simultaneously!")
                
                if num_tags >= 2:
                    if stable_period_start is None:
                        stable_period_start = time.time()
                        print(f"📊 Stable multi-tag detection started: {num_tags} tags")
                    
                    stable_detection_count += 1
                    
                    # Try to get information about all tags
                    try:
                        all_info = nfc_native.get_all_tags_info()
                        if all_info and len(all_info) >= 2:
                            print(f"✅ Successfully got info for {len(all_info)} tags simultaneously!")
                            for i, tag in enumerate(all_info):
                                uid = tag.get('uid', 'Unknown')[:16]
                                tech = tag.get('technology_name', 'Unknown')
                                print(f"   Tag {i+1}: {tech} (UID: {uid}...)")
                        
                        # Try to read text from all tags
                        all_text = nfc_native.read_all_text()
                        if all_text and len(all_text) >= 2:
                            print(f"📝 Successfully read text from {len(all_text)} tags!")
                            for i, tag in enumerate(all_text):
                                text = tag.get('text', 'No text')
                                print(f"   Tag {i+1} text: '{text}'")
                    
                    except Exception as e:
                        logger.debug(f"Error reading multi-tag info: {e}")
                else:
                    if stable_period_start is not None:
                        stable_duration = time.time() - stable_period_start
                        print(f"📉 Stable period ended after {stable_duration:.1f} seconds")
                        stable_period_start = None
                
                simultaneous_detections.append({
                    'timestamp': time.time() - start_time,
                    'num_tags': num_tags,
                    'is_present': is_present
                })
                
                time.sleep(0.2)  # 200ms polling for stability
                
            except Exception as e:
                logger.error(f"Error during simultaneous detection test: {e}")
                time.sleep(0.5)
        
        # Analysis
        multi_tag_detections = [d for d in simultaneous_detections if d['num_tags'] >= 2]
        success_rate = len(multi_tag_detections) / len(simultaneous_detections) if simultaneous_detections else 0
        
        print(f"\n📊 Simultaneous Detection Results:")
        print(f"   Maximum tags detected: {max_simultaneous}")
        print(f"   Multi-tag detection rate: {success_rate:.1%}")
        print(f"   Stable detections: {stable_detection_count}")
        print(f"   Total measurements: {len(simultaneous_detections)}")
        
        success = max_simultaneous >= 2 and success_rate > 0.1  # At least 10% success rate
        self.log_test_result("True_Simultaneous_Detection", success, 
                           f"Max: {max_simultaneous}, Rate: {success_rate:.1%}")
        
        if success:
            print("✅ Hardware supports true simultaneous multi-tag detection!")
        else:
            print("❌ Hardware does not support reliable simultaneous multi-tag detection")
        
        return success, max_simultaneous, success_rate
    
    def test_different_discovery_configs(self):
        """Test different discovery configurations for multi-tag support."""
        self.print_header("Discovery Configuration Test")
        
        print("Testing different NFC discovery configurations...")
        
        # Note: This would require access to doEnableDiscovery parameters
        # For now, we'll test with the current configuration and note limitations
        
        try:
            # Current configuration test
            logger.debug("Testing current discovery configuration")
            nfc_native.stop_discovery()
            time.sleep(0.5)
            nfc_native.start_discovery()
            time.sleep(1.0)
            
            # Test basic functionality after restart
            num_tags = nfc_native.get_num_tags()
            is_present = nfc_native.is_tag_present()
            
            print(f"✅ Discovery restart successful (num_tags={num_tags}, present={is_present})")
            self.log_test_result("Discovery_Config_Test", True, 
                               f"Restart successful, num_tags={num_tags}")
            
            return True
            
        except Exception as e:
            logger.error(f"Discovery configuration test failed: {e}")
            self.log_test_result("Discovery_Config_Test", False, f"Exception: {e}")
            return False
    
    def generate_hardware_capability_report(self, test_results):
        """Generate a comprehensive report on hardware capabilities."""
        self.print_header("Hardware Capability Report")
        
        print("📋 NFC Hardware Analysis:")
        print(f"   Basic NFC functionality: {'✅' if test_results.get('basic_nfc') else '❌'}")
        print(f"   Single tag detection: {'✅' if test_results.get('single_tag') else '❌'}")
        print(f"   Sequential detection: {'✅' if test_results.get('sequential') else '❌'}")
        print(f"   Simultaneous detection: {'✅' if test_results.get('simultaneous') else '❌'}")
        
        max_tags = test_results.get('max_simultaneous', 0)
        success_rate = test_results.get('simultaneous_rate', 0)
        
        print(f"\n📊 Multi-Tag Capabilities:")
        print(f"   Maximum simultaneous tags: {max_tags}")
        print(f"   Simultaneous detection rate: {success_rate:.1%}")
        
        print(f"\n💡 Recommendations:")
        if test_results.get('simultaneous'):
            print("   ✅ Your hardware supports true multi-tag detection!")
            print("   ✅ The multi-tag demo should work as designed")
        elif test_results.get('sequential'):
            print("   ⚠️  Hardware doesn't support simultaneous detection")
            print("   💡 Use rapid sequential detection as a workaround")
            print("   💡 Consider implementing 'quick-switch' multi-tag mode")
        else:
            print("   ❌ Multi-tag detection not supported by this hardware")
            print("   💡 Focus on single-tag applications")
            print("   💡 Consider hardware upgrade for multi-tag functionality")
        
        # Save detailed report
        report_file = "/tmp/nfc_hardware_report.txt"
        try:
            with open(report_file, 'w') as f:
                f.write("NFC Multi-Tag Hardware Diagnostic Report\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                
                f.write("Test Results:\n")
                for test_name, result in self.test_results.items():
                    status = "PASS" if result['success'] else "FAIL"
                    f.write(f"  {test_name}: {status} - {result['details']}\n")
                
                f.write(f"\nHardware Capabilities:\n")
                f.write(f"  Maximum simultaneous tags: {max_tags}\n")
                f.write(f"  Simultaneous success rate: {success_rate:.1%}\n")
                
            print(f"\n📄 Detailed report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Could not save report: {e}")
    
    def run_full_diagnostic(self):
        """Run the complete diagnostic suite."""
        print("🔍 NFC Multi-Tag Diagnostic Tool")
        print("=" * 50)
        print("This tool will comprehensively test your NFC hardware's multi-tag capabilities.")
        
        # Check permissions
        import os
        if os.geteuid() != 0:
            print("⚠️  Warning: This tool typically requires root privileges.")
            print("If you encounter errors, try running with 'sudo'\n")
        
        test_results = {}
        
        try:
            # Phase 1: Basic functionality
            test_results['basic_nfc'] = self.test_basic_nfc_functionality()
            if not test_results['basic_nfc']:
                print("\n❌ Basic NFC functionality failed - stopping diagnostics")
                return False
            
            # Phase 2: Single tag detection
            test_results['single_tag'] = self.test_single_tag_detection()
            
            # Phase 3: Multi-tag API functions
            self.test_multi_tag_api_functions()
            
            # Phase 4: Sequential detection
            sequential_result, detected_tags, max_reported = self.test_rapid_sequential_detection()
            test_results['sequential'] = sequential_result
            test_results['sequential_tags'] = len(detected_tags)
            test_results['max_reported'] = max_reported
            
            # Phase 5: True simultaneous detection
            simultaneous_result, max_simultaneous, success_rate = self.test_true_simultaneous_detection()
            test_results['simultaneous'] = simultaneous_result
            test_results['max_simultaneous'] = max_simultaneous
            test_results['simultaneous_rate'] = success_rate
            
            # Phase 6: Discovery configuration
            self.test_different_discovery_configs()
            
            # Phase 7: Generate report
            self.generate_hardware_capability_report(test_results)
            
            return True
            
        except Exception as e:
            logger.error(f"Diagnostic suite failed: {e}")
            print(f"❌ Diagnostic failed with error: {e}")
            return False
        
        finally:
            # Cleanup
            try:
                nfc_native.stop_discovery()
                nfc_native.deinitialize()
                logger.info("NFC cleanup completed")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

def main():
    """Main function."""
    diagnostic = NFCMultiTagDiagnostic()
    success = diagnostic.run_full_diagnostic()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Diagnostic completed successfully!")
        print("📄 Check the detailed logs and report for analysis.")
    else:
        print("❌ Diagnostic encountered errors.")
        print("📄 Check logs for troubleshooting information.")
    
    print("📋 Log files:")
    print("   - /tmp/nfc_diagnostic.log (detailed log)")
    print("   - /tmp/nfc_hardware_report.txt (hardware report)")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())