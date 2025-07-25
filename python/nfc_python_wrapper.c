/******************************************************************************
 *
 *  Python C Extension Wrapper for Linux NFC API
 *  Copyright 2025
 *
 *  Licensed under the Apache License, Version 2.0 (the "License")
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 ******************************************************************************/

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "linux_nfc_api.h"
#include <string.h>
#include <stdlib.h>
#include <time.h>

static int nfc_initialized = 0;
static char* last_text_found = NULL;
static char* last_language_found = NULL;

// Global variables for tag detection
static nfcTagCallback_t python_tag_callback;
static int tag_detected = 0;
static nfc_tag_info_t detected_tag_info;
static ndef_info_t detected_ndef_info;

// Tag callback functions
static void onTagArrival(nfc_tag_info_t *pTagInfo) {
    if (pTagInfo) {
        printf("[DEBUG] onTagArrival called - UID: ");
        for (int i = 0; i < pTagInfo->uid_length && i < 8; i++) {
            printf("%02X", (unsigned char)pTagInfo->uid[i]);
        }
        printf(", Tech: %d\n", pTagInfo->technology);
        
        memcpy(&detected_tag_info, pTagInfo, sizeof(nfc_tag_info_t));
        tag_detected = 1;
        
        // Check how many tags the system thinks we have
        int current_num_tags = getNumTags();
        printf("[DEBUG] onTagArrival: getNumTags() now returns %d\n", current_num_tags);
    }
}

static void onTagDeparture(void) {
    printf("[DEBUG] onTagDeparture called\n");
    tag_detected = 0;
    
    int current_num_tags = getNumTags();
    printf("[DEBUG] onTagDeparture: getNumTags() now returns %d\n", current_num_tags);
}

// Python wrapper for doInitialize
static PyObject* py_nfc_initialize(PyObject* self, PyObject* args) {
    if (nfc_initialized) {
        Py_RETURN_TRUE;
    }
    
    InitializeLogLevel();
    
    int result = doInitialize();
    if (result == 0) {
        nfc_initialized = 1;
        
        // Setup tag callbacks
        python_tag_callback.onTagArrival = onTagArrival;
        python_tag_callback.onTagDeparture = onTagDeparture;
        registerTagCallback(&python_tag_callback);
        
        Py_RETURN_TRUE;
    }
    
    Py_RETURN_FALSE;
}

// Python wrapper for doDeinitialize
static PyObject* py_nfc_deinitialize(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        Py_RETURN_TRUE;
    }
    
    disableDiscovery();
    deregisterTagCallback();
    doDeinitialize();
    nfc_initialized = 0;
    
    // Clean up stored text
    if (last_text_found) {
        free(last_text_found);
        last_text_found = NULL;
    }
    if (last_language_found) {
        free(last_language_found);
        last_language_found = NULL;
    }
    
    Py_RETURN_TRUE;
}

// Python wrapper for enabling discovery
static PyObject* py_nfc_start_discovery(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    doEnableDiscovery(DEFAULT_NFA_TECH_MASK, 0, 0, 0);
    Py_RETURN_NONE;
}

// Python wrapper for disabling discovery
static PyObject* py_nfc_stop_discovery(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    disableDiscovery();
    Py_RETURN_NONE;
}

// Check if a tag is present
static PyObject* py_nfc_is_tag_present(PyObject* self, PyObject* args) {
    if (tag_detected) {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

// Read text from the detected tag
static PyObject* py_nfc_read_text(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    if (!tag_detected) {
        Py_RETURN_NONE;
    }
    
    // Check if tag is NDEF
    int is_ndef = nfcTag_isNdef(detected_tag_info.handle, &detected_ndef_info);
    if (!is_ndef) {
        Py_RETURN_NONE;
    }
    
    // Read NDEF data
    unsigned char* ndef_buffer = malloc(detected_ndef_info.current_ndef_length);
    if (!ndef_buffer) {
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate NDEF buffer");
        return NULL;
    }
    
    nfc_friendly_type_t friendly_type;
    int bytes_read = nfcTag_readNdef(detected_tag_info.handle, ndef_buffer, 
                                   detected_ndef_info.current_ndef_length, &friendly_type);
    
    if (bytes_read <= 0) {
        free(ndef_buffer);
        Py_RETURN_NONE;
    }
    
    // Check if it's a text record
    if (friendly_type != NDEF_FRIENDLY_TYPE_TEXT) {
        free(ndef_buffer);
        Py_RETURN_NONE;
    }
    
    // Extract text and language
    char text_buffer[1024];
    char lang_buffer[16];
    
    int lang_len = ndef_readLanguageCode(ndef_buffer, bytes_read, lang_buffer, sizeof(lang_buffer));
    int text_len = ndef_readText(ndef_buffer, bytes_read, text_buffer, sizeof(text_buffer));
    
    free(ndef_buffer);
    
    if (text_len <= 0 || lang_len <= 0) {
        Py_RETURN_NONE;
    }
    
    // Null terminate strings
    text_buffer[text_len] = '\0';
    lang_buffer[lang_len] = '\0';
    
    // Store for later retrieval
    if (last_text_found) {
        free(last_text_found);
    }
    if (last_language_found) {
        free(last_language_found);
    }
    
    last_text_found = malloc(text_len + 1);
    last_language_found = malloc(lang_len + 1);
    
    if (last_text_found && last_language_found) {
        strcpy(last_text_found, text_buffer);
        strcpy(last_language_found, lang_buffer);
        
        // Return dictionary with text and language
        PyObject* result = PyDict_New();
        PyDict_SetItemString(result, "text", PyUnicode_FromString(text_buffer));
        PyDict_SetItemString(result, "language", PyUnicode_FromString(lang_buffer));
        PyDict_SetItemString(result, "type", PyUnicode_FromString("text"));
        
        return result;
    }
    
    Py_RETURN_NONE;
}

// Get tag information
static PyObject* py_nfc_get_tag_info(PyObject* self, PyObject* args) {
    if (!tag_detected) {
        Py_RETURN_NONE;
    }
    
    PyObject* result = PyDict_New();
    PyDict_SetItemString(result, "technology", PyLong_FromLong(detected_tag_info.technology));
    PyDict_SetItemString(result, "handle", PyLong_FromLong(detected_tag_info.handle));
    PyDict_SetItemString(result, "uid_length", PyLong_FromLong(detected_tag_info.uid_length));
    
    // Convert UID to hex string
    if (detected_tag_info.uid_length > 0) {
        char uid_str[65]; // Max 32 bytes * 2 + 1
        uid_str[0] = '\0';
        for (int i = 0; i < detected_tag_info.uid_length && i < 32; i++) {
            char hex_byte[3];
            sprintf(hex_byte, "%02X", (unsigned char)detected_tag_info.uid[i]);
            strcat(uid_str, hex_byte);
        }
        PyDict_SetItemString(result, "uid", PyUnicode_FromString(uid_str));
    }
    
    // Add technology name
    const char* tech_name = "Unknown";
    switch (detected_tag_info.technology) {
        case TARGET_TYPE_ISO14443_3A: tech_name = "Type A"; break;
        case TARGET_TYPE_ISO14443_3B: tech_name = "Type B"; break;
        case TARGET_TYPE_ISO14443_4: tech_name = "Type 4A"; break;
        case TARGET_TYPE_FELICA: tech_name = "Type F"; break;
        case TARGET_TYPE_ISO15693: tech_name = "Type V"; break;
        case TARGET_TYPE_NDEF: tech_name = "NDEF"; break;
        case TARGET_TYPE_NDEF_FORMATABLE: tech_name = "NDEF Formatable"; break;
        case TARGET_TYPE_MIFARE_CLASSIC: tech_name = "Mifare Classic"; break;
        case TARGET_TYPE_MIFARE_UL: tech_name = "Mifare Ultralight"; break;
        case TARGET_TYPE_KOVIO_BARCODE: tech_name = "Kovio Barcode"; break;
    }
    PyDict_SetItemString(result, "technology_name", PyUnicode_FromString(tech_name));
    
    return result;
}

// Get number of detected tags
static PyObject* py_nfc_get_num_tags(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    int num_tags = getNumTags();
    
    // Debug logging
    static int last_num_tags = -1;
    if (num_tags != last_num_tags) {
        printf("[DEBUG] getNumTags() returned: %d (changed from %d)\n", num_tags, last_num_tags);
        last_num_tags = num_tags;
    }
    
    return PyLong_FromLong(num_tags);
}

// Select next tag in the field
static PyObject* py_nfc_select_next_tag(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    printf("[DEBUG] selectNextTag() called\n");
    int result = selectNextTag();
    printf("[DEBUG] selectNextTag() returned: %d\n", result);
    
    if (result == 0) {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

// Check next valid protocol
static PyObject* py_nfc_check_next_protocol(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    int protocol_index = checkNextProtocol();
    return PyLong_FromLong(protocol_index);
}

// Read text from all detected tags
static PyObject* py_nfc_read_all_text(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    int num_tags = getNumTags();
    printf("[DEBUG] read_all_text: getNumTags() returned %d\n", num_tags);
    
    if (num_tags <= 0) {
        printf("[DEBUG] read_all_text: No tags detected, returning None\n");
        Py_RETURN_NONE;
    }
    
    PyObject* tag_list = PyList_New(0);
    if (!tag_list) {
        return NULL;
    }
    
    // Store original tag state
    int original_tag_detected = tag_detected;
    nfc_tag_info_t original_tag_info;
    if (tag_detected) {
        memcpy(&original_tag_info, &detected_tag_info, sizeof(nfc_tag_info_t));
    }
    
    // Read from each tag
    for (int i = 0; i < num_tags; i++) {
        printf("[DEBUG] read_all_text: Processing tag %d of %d\n", i+1, num_tags);
        
        PyObject* tag_data = PyDict_New();
        if (!tag_data) {
            Py_DECREF(tag_list);
            return NULL;
        }
        
        // Add tag index
        PyDict_SetItemString(tag_data, "tag_index", PyLong_FromLong(i));
        
        // Get text from current tag
        PyObject* text_result = py_nfc_read_text(self, args);
        if (text_result && text_result != Py_None) {
            // Merge text data into tag_data
            if (PyDict_Check(text_result)) {
                PyObject* key, *value;
                Py_ssize_t pos = 0;
                while (PyDict_Next(text_result, &pos, &key, &value)) {
                    PyDict_SetItem(tag_data, key, value);
                }
            }
        }
        Py_XDECREF(text_result);
        
        // Get tag info
        PyObject* info_result = py_nfc_get_tag_info(self, args);
        if (info_result && info_result != Py_None) {
            // Merge tag info into tag_data
            if (PyDict_Check(info_result)) {
                PyObject* key, *value;
                Py_ssize_t pos = 0;
                while (PyDict_Next(info_result, &pos, &key, &value)) {
                    PyDict_SetItem(tag_data, key, value);
                }
            }
        }
        Py_XDECREF(info_result);
        
        PyList_Append(tag_list, tag_data);
        Py_DECREF(tag_data);
        
        // Select next tag if not the last one
        if (i < num_tags - 1) {
            printf("[DEBUG] read_all_text: Selecting next tag...\n");
            int select_result = selectNextTag();
            printf("[DEBUG] read_all_text: selectNextTag() returned %d\n", select_result);
            
            // Small delay to allow tag switch
            struct timespec ts = {0, 50000000}; // 50ms
            nanosleep(&ts, NULL);
            
            // Check if tag count changed
            int new_num_tags = getNumTags();
            printf("[DEBUG] read_all_text: After selectNextTag, getNumTags() = %d\n", new_num_tags);
        }
    }
    
    // Restore original tag state if possible
    if (original_tag_detected) {
        tag_detected = original_tag_detected;
        memcpy(&detected_tag_info, &original_tag_info, sizeof(nfc_tag_info_t));
    }
    
    return tag_list;
}

// Create NDEF text record
static PyObject* py_nfc_create_text_ndef(PyObject* self, PyObject* args) {
    const char* language_code;
    const char* text;
    
    if (!PyArg_ParseTuple(args, "ss", &language_code, &text)) {
        return NULL;
    }
    
    if (!language_code || !text) {
        PyErr_SetString(PyExc_ValueError, "Language code and text cannot be NULL");
        return NULL;
    }
    
    // Calculate buffer size (text + language + NDEF overhead)
    unsigned int buffer_size = strlen(text) + strlen(language_code) + 50;
    unsigned char* ndef_buffer = malloc(buffer_size);
    if (!ndef_buffer) {
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate NDEF buffer");
        return NULL;
    }
    
    int ndef_size = ndef_createText((char*)language_code, (char*)text, ndef_buffer, buffer_size);
    if (ndef_size <= 0) {
        free(ndef_buffer);
        PyErr_SetString(PyExc_RuntimeError, "Failed to create NDEF text record");
        return NULL;
    }
    
    // Return NDEF data as bytes object
    PyObject* result = PyBytes_FromStringAndSize((char*)ndef_buffer, ndef_size);
    free(ndef_buffer);
    
    return result;
}

// Write NDEF data to current tag
static PyObject* py_nfc_write_ndef(PyObject* self, PyObject* args) {
    const char* ndef_data;
    Py_ssize_t ndef_length;
    
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    if (!tag_detected) {
        PyErr_SetString(PyExc_RuntimeError, "No tag detected");
        return NULL;
    }
    
    if (!PyArg_ParseTuple(args, "y#", &ndef_data, &ndef_length)) {
        return NULL;
    }
    
    if (!ndef_data || ndef_length <= 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid NDEF data");
        return NULL;
    }
    
    int result = nfcTag_writeNdef(detected_tag_info.handle, (unsigned char*)ndef_data, ndef_length);
    if (result != 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to write NDEF data to tag");
        return NULL;
    }
    
    Py_RETURN_TRUE;
}

// Write text to current tag (convenience function)
static PyObject* py_nfc_write_text(PyObject* self, PyObject* args) {
    const char* language_code = "en";
    const char* text;
    
    if (!PyArg_ParseTuple(args, "s|s", &text, &language_code)) {
        return NULL;
    }
    
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    if (!tag_detected) {
        PyErr_SetString(PyExc_RuntimeError, "No tag detected");
        return NULL;
    }
    
    // Create NDEF text record
    unsigned int buffer_size = strlen(text) + strlen(language_code) + 50;
    unsigned char* ndef_buffer = malloc(buffer_size);
    if (!ndef_buffer) {
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate NDEF buffer");
        return NULL;
    }
    
    int ndef_size = ndef_createText((char*)language_code, (char*)text, ndef_buffer, buffer_size);
    if (ndef_size <= 0) {
        free(ndef_buffer);
        PyErr_SetString(PyExc_RuntimeError, "Failed to create NDEF text record");
        return NULL;
    }
    
    // Write to tag
    int result = nfcTag_writeNdef(detected_tag_info.handle, ndef_buffer, ndef_size);
    free(ndef_buffer);
    
    if (result != 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to write text to tag");
        return NULL;
    }
    
    Py_RETURN_TRUE;
}

// Get information for all detected tags
static PyObject* py_nfc_get_all_tags_info(PyObject* self, PyObject* args) {
    if (!nfc_initialized) {
        PyErr_SetString(PyExc_RuntimeError, "NFC not initialized");
        return NULL;
    }
    
    int num_tags = getNumTags();
    if (num_tags <= 0) {
        Py_RETURN_NONE;
    }
    
    PyObject* tag_list = PyList_New(0);
    if (!tag_list) {
        return NULL;
    }
    
    // Store original tag state
    int original_tag_detected = tag_detected;
    nfc_tag_info_t original_tag_info;
    if (tag_detected) {
        memcpy(&original_tag_info, &detected_tag_info, sizeof(nfc_tag_info_t));
    }
    
    // Read info from each tag
    for (int i = 0; i < num_tags; i++) {
        PyObject* tag_info = py_nfc_get_tag_info(self, args);
        if (tag_info && tag_info != Py_None) {
            // Add tag index
            PyDict_SetItemString(tag_info, "tag_index", PyLong_FromLong(i));
            PyList_Append(tag_list, tag_info);
        }
        Py_XDECREF(tag_info);
        
        // Select next tag if not the last one
        if (i < num_tags - 1) {
            selectNextTag();
            // Small delay to allow tag switch
            struct timespec ts = {0, 50000000}; // 50ms
            nanosleep(&ts, NULL);
        }
    }
    
    // Restore original tag state if possible
    if (original_tag_detected) {
        tag_detected = original_tag_detected;
        memcpy(&detected_tag_info, &original_tag_info, sizeof(nfc_tag_info_t));
    }
    
    return tag_list;
}

// Method definitions
static PyMethodDef NFCMethods[] = {
    {"initialize", py_nfc_initialize, METH_NOARGS, "Initialize NFC stack"},
    {"deinitialize", py_nfc_deinitialize, METH_NOARGS, "Deinitialize NFC stack"},
    {"start_discovery", py_nfc_start_discovery, METH_NOARGS, "Start tag discovery"},
    {"stop_discovery", py_nfc_stop_discovery, METH_NOARGS, "Stop tag discovery"},
    {"is_tag_present", py_nfc_is_tag_present, METH_NOARGS, "Check if tag is present"},
    {"read_text", py_nfc_read_text, METH_NOARGS, "Read text from NDEF tag"},
    {"get_tag_info", py_nfc_get_tag_info, METH_NOARGS, "Get tag information"},
    {"get_num_tags", py_nfc_get_num_tags, METH_NOARGS, "Get number of detected tags"},
    {"select_next_tag", py_nfc_select_next_tag, METH_NOARGS, "Select next tag in field"},
    {"check_next_protocol", py_nfc_check_next_protocol, METH_NOARGS, "Check next valid protocol"},
    {"read_all_text", py_nfc_read_all_text, METH_NOARGS, "Read text from all detected tags"},
    {"get_all_tags_info", py_nfc_get_all_tags_info, METH_NOARGS, "Get info for all detected tags"},
    {"create_text_ndef", py_nfc_create_text_ndef, METH_VARARGS, "Create NDEF text record"},
    {"write_ndef", py_nfc_write_ndef, METH_VARARGS, "Write NDEF data to tag"},
    {"write_text", py_nfc_write_text, METH_VARARGS, "Write text to tag"},
    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef nfcmodule = {
    PyModuleDef_HEAD_INIT,
    "nfc_native",
    "Python interface for Linux NFC API",
    -1,
    NFCMethods
};

// Module initialization
PyMODINIT_FUNC PyInit_nfc_native(void) {
    return PyModule_Create(&nfcmodule);
}