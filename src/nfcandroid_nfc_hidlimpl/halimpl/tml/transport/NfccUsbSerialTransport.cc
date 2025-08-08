/******************************************************************************
 *
 *  Copyright 2024 FlowOS Project
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
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

#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <termios.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/stat.h>

#include <NfccUsbSerialTransport.h>
#include <phNfcStatus.h>
#include <phNxpLog.h>

#define USB_SERIAL_TIMEOUT_SEC 5
#define MAX_RESPONSE_SIZE 1024
#define MAX_COMMAND_SIZE 512

/*******************************************************************************
**
** Function         OpenAndConfigure
**
** Description      Open and configure USB serial bridge connection to Pico 2 W
**
** Parameters       pConfig     - hardware information
**                  pLinkHandle - device handle
**
** Returns          NFC status:
**                  NFCSTATUS_SUCCESS - open_and_configure operation success
**                  NFCSTATUS_INVALID_DEVICE - device open operation failure
**
*******************************************************************************/
NFCSTATUS NfccUsbSerialTransport::OpenAndConfigure(pphTmlNfc_Config_t pConfig,
                                                   void** pLinkHandle) {
    NXPLOG_TML_D("%s Enter", __func__);
    
    // Initialize member variables
    m_serial_fd = -1;
    m_fw_dwnld_mode = false;
    memset(m_device_path, 0, sizeof(m_device_path));
    
    // Find USB serial device (Pico 2 W CDC)
    if (FindSerialDevice(m_device_path, sizeof(m_device_path)) != 0) {
        NXPLOG_TML_E("Could not find USB serial bridge device");
        return NFCSTATUS_INVALID_DEVICE;
    }
    
    NXPLOG_TML_D("Found USB serial device: %s", m_device_path);
    
    // Open serial port
    m_serial_fd = open(m_device_path, O_RDWR | O_NOCTTY | O_SYNC);
    if (m_serial_fd < 0) {
        NXPLOG_TML_E("Could not open USB serial device '%s' (%s)", 
                     m_device_path, strerror(errno));
        return NFCSTATUS_INVALID_DEVICE;
    }
    
    // Configure serial port
    if (SetupSerial(m_serial_fd) != 0) {
        NXPLOG_TML_E("Failed to configure serial port");
        close(m_serial_fd);
        m_serial_fd = -1;
        return NFCSTATUS_INVALID_DEVICE;
    }
    
    // Test communication with bridge
    char response[MAX_RESPONSE_SIZE];
    if (SendCommand(m_serial_fd, "PING", response, sizeof(response)) <= 0) {
        NXPLOG_TML_E("Failed to communicate with USB serial bridge");
        close(m_serial_fd);
        m_serial_fd = -1;
        return NFCSTATUS_INVALID_DEVICE;
    }
    
    // Initialize NFC chip via bridge
    if (SendCommand(m_serial_fd, "INIT", response, sizeof(response)) <= 0) {
        NXPLOG_TML_E("Failed to initialize NFC chip via bridge");
        close(m_serial_fd);
        m_serial_fd = -1;
        return NFCSTATUS_INVALID_DEVICE;
    }
    
    *pLinkHandle = (void*)((intptr_t)m_serial_fd);
    
    // Reset NFC chip to power on state
    NfccReset((void*)((intptr_t)m_serial_fd), MODE_POWER_OFF);
    NfccReset((void*)((intptr_t)m_serial_fd), MODE_POWER_ON);
    
    NXPLOG_TML_D("%s exit - SUCCESS", __func__);
    return NFCSTATUS_SUCCESS;
}

/*******************************************************************************
**
** Function         Read
**
** Description      Reads requested number of bytes from NFCC device via USB
**                  serial bridge
**
** Parameters       pDevHandle       - valid device handle
**                  pBuffer          - buffer for read data
**                  nNbBytesToRead   - number of bytes requested to be read
**
** Returns          numRead   - number of successfully read bytes
**                  -1        - read operation failure
**
*******************************************************************************/
int NfccUsbSerialTransport::Read(void* pDevHandle, uint8_t* pBuffer, int nNbBytesToRead) {
    NXPLOG_TML_D("%s Enter", __func__);
    
    if (NULL == pDevHandle || NULL == pBuffer) {
        NXPLOG_TML_E("%s Invalid parameters", __func__);
        return -1;
    }
    
    int fd = (intptr_t)pDevHandle;
    char command[MAX_COMMAND_SIZE];
    char response[MAX_RESPONSE_SIZE];
    
    // Send read command to bridge
    snprintf(command, sizeof(command), "READ:%d", nNbBytesToRead);
    
    int response_len = SendCommand(fd, command, response, sizeof(response));
    if (response_len <= 0) {
        NXPLOG_TML_E("Failed to send READ command to bridge");
        return -1;
    }
    
    // Parse response: "OK:hexdata" or "ERROR:code"
    if (strncmp(response, "OK:", 3) != 0) {
        NXPLOG_TML_E("Bridge returned error: %s", response);
        return -1;
    }
    
    // Convert hex data to binary
    char* hex_data = response + 3;
    int hex_len = strlen(hex_data);
    int bytes_read = 0;
    
    for (int i = 0; i < hex_len && bytes_read < nNbBytesToRead; i += 2) {
        if (i + 1 >= hex_len) break;
        
        char hex_byte[3] = {hex_data[i], hex_data[i+1], '\0'};
        pBuffer[bytes_read] = (uint8_t)strtol(hex_byte, NULL, 16);
        bytes_read++;
    }
    
    NXPLOG_TML_D("%s exit - read %d bytes", __func__, bytes_read);
    return bytes_read;
}

/*******************************************************************************
**
** Function         Write
**
** Description      Writes requested number of bytes to NFCC device via USB
**                  serial bridge
**
** Parameters       pDevHandle       - valid device handle
**                  pBuffer          - buffer with write data
**                  nNbBytesToWrite  - number of bytes requested to be written
**
** Returns          numWrote   - number of successfully written bytes
**                  -1         - write operation failure
**
*******************************************************************************/
int NfccUsbSerialTransport::Write(void* pDevHandle, uint8_t* pBuffer, int nNbBytesToWrite) {
    NXPLOG_TML_D("%s Enter", __func__);
    
    if (NULL == pDevHandle || NULL == pBuffer || nNbBytesToWrite <= 0) {
        NXPLOG_TML_E("%s Invalid parameters", __func__);
        return -1;
    }
    
    int fd = (intptr_t)pDevHandle;
    char command[MAX_COMMAND_SIZE];
    char response[MAX_RESPONSE_SIZE];
    
    // Convert binary data to hex string
    char hex_data[MAX_COMMAND_SIZE - 10]; // Reserve space for "WRITE:" prefix
    int hex_pos = 0;
    
    for (int i = 0; i < nNbBytesToWrite && hex_pos < sizeof(hex_data) - 3; i++) {
        sprintf(hex_data + hex_pos, "%02X", pBuffer[i]);
        hex_pos += 2;
    }
    hex_data[hex_pos] = '\0';
    
    // Send write command to bridge
    snprintf(command, sizeof(command), "WRITE:%s", hex_data);
    
    int response_len = SendCommand(fd, command, response, sizeof(response));
    if (response_len <= 0) {
        NXPLOG_TML_E("Failed to send WRITE command to bridge");
        return -1;
    }
    
    // Parse response: "OK:bytes_written" or "ERROR:code"
    if (strncmp(response, "OK:", 3) != 0) {
        NXPLOG_TML_E("Bridge returned error: %s", response);
        return -1;
    }
    
    int bytes_written = atoi(response + 3);
    
    NXPLOG_TML_D("%s exit - wrote %d bytes", __func__, bytes_written);
    return bytes_written;
}

/*******************************************************************************
**
** Function         Close
**
** Description      Closes USB serial bridge connection
**
** Parameters       pDevHandle - device handle
**
** Returns          None
**
*******************************************************************************/
void NfccUsbSerialTransport::Close(void* pDevHandle) {
    NXPLOG_TML_D("%s Enter", __func__);
    
    if (NULL != pDevHandle) {
        close((intptr_t)pDevHandle);
    }
    
    if (m_serial_fd >= 0) {
        close(m_serial_fd);
        m_serial_fd = -1;
    }
    
    NXPLOG_TML_D("%s exit", __func__);
}

/*******************************************************************************
**
** Function         NfccReset
**
** Description      Reset NFCC device via USB serial bridge GPIO commands
**
** Parameters       pDevHandle     - valid device handle
**                  eType          - NfccResetType
**
** Returns           0   - reset operation success
**                  -1   - reset operation failure
**
*******************************************************************************/
int NfccUsbSerialTransport::NfccReset(void* pDevHandle, NfccResetType eType) {
    NXPLOG_TML_D("%s Enter - type: %d", __func__, eType);
    
    if (NULL == pDevHandle) {
        return -1;
    }
    
    int fd = (intptr_t)pDevHandle;
    char command[MAX_COMMAND_SIZE];
    char response[MAX_RESPONSE_SIZE];
    
    switch (eType) {
        case MODE_POWER_OFF:
            snprintf(command, sizeof(command), "GPIO_SET:VEN:0");
            m_fw_dwnld_mode = false;
            break;
            
        case MODE_POWER_ON:
            snprintf(command, sizeof(command), "GPIO_SET:VEN:1");
            m_fw_dwnld_mode = false;
            break;
            
        case MODE_FW_DWNLD_WITH_VEN:
            snprintf(command, sizeof(command), "GPIO_SET:FWDL:1");
            m_fw_dwnld_mode = true;
            break;
            
        case MODE_FW_GPIO_LOW:
            snprintf(command, sizeof(command), "GPIO_SET:FWDL:0");
            m_fw_dwnld_mode = false;
            break;
            
        default:
            NXPLOG_TML_E("Unsupported reset type: %d", eType);
            return -1;
    }
    
    int response_len = SendCommand(fd, command, response, sizeof(response));
    if (response_len <= 0 || strncmp(response, "OK", 2) != 0) {
        NXPLOG_TML_E("Reset command failed: %s", response);
        return -1;
    }
    
    // Add delay for reset to take effect
    usleep(10000); // 10ms
    
    NXPLOG_TML_D("%s exit - SUCCESS", __func__);
    return 0;
}

/*******************************************************************************
**
** Function         GetIrqState
**
** Description      Get state of IRQ GPIO via USB serial bridge
**
** Parameters       pDevHandle - valid device handle
**
** Returns          The state of IRQ line i.e. +ve if read is pending else 0.
**                  In the case of communication error, returns -ve value.
**
*******************************************************************************/
int NfccUsbSerialTransport::GetIrqState(void* pDevHandle) {
    if (NULL == pDevHandle) {
        return -1;
    }
    
    int fd = (intptr_t)pDevHandle;
    char response[MAX_RESPONSE_SIZE];
    
    int response_len = SendCommand(fd, "GPIO_GET:IRQ", response, sizeof(response));
    if (response_len <= 0) {
        return -1;
    }
    
    // Parse response: "OK:1" or "OK:0"
    if (strncmp(response, "OK:", 3) != 0) {
        return -1;
    }
    
    return atoi(response + 3);
}

/*******************************************************************************
**
** Function         SendCommand
**
** Description      Send command to USB serial bridge and wait for response
**
** Parameters       fd           - serial device file descriptor
**                  command      - command string to send
**                  response     - buffer for response
**                  max_response - maximum response buffer size
**
** Returns          Response length on success, -1 on failure
**
*******************************************************************************/
int NfccUsbSerialTransport::SendCommand(int fd, const char* command, char* response, int max_response) {
    if (fd < 0 || !command || !response || max_response <= 0) {
        return -1;
    }
    
    // Send command with newline terminator
    char cmd_with_newline[MAX_COMMAND_SIZE + 2];
    snprintf(cmd_with_newline, sizeof(cmd_with_newline), "%s\n", command);
    
    ssize_t written = write(fd, cmd_with_newline, strlen(cmd_with_newline));
    if (written != (ssize_t)strlen(cmd_with_newline)) {
        return -1;
    }
    
    // Wait for response with timeout
    fd_set read_fds;
    struct timeval timeout;
    FD_ZERO(&read_fds);
    FD_SET(fd, &read_fds);
    timeout.tv_sec = USB_SERIAL_TIMEOUT_SEC;
    timeout.tv_usec = 0;
    
    int select_result = select(fd + 1, &read_fds, NULL, NULL, &timeout);
    if (select_result <= 0) {
        return -1; // Timeout or error
    }
    
    // Read response
    ssize_t bytes_read = read(fd, response, max_response - 1);
    if (bytes_read <= 0) {
        return -1;
    }
    
    response[bytes_read] = '\0';
    
    // Remove trailing newline if present
    if (bytes_read > 0 && response[bytes_read - 1] == '\n') {
        response[bytes_read - 1] = '\0';
        bytes_read--;
    }
    
    return (int)bytes_read;
}

/*******************************************************************************
**
** Function         SetupSerial
**
** Description      Configure serial port parameters
**
** Parameters       fd - serial device file descriptor
**
** Returns          0 on success, -1 on failure
**
*******************************************************************************/
int NfccUsbSerialTransport::SetupSerial(int fd) {
    struct termios tty;
    
    if (tcgetattr(fd, &tty) != 0) {
        return -1;
    }
    
    // Set baud rate to 115200
    cfsetospeed(&tty, B115200);
    cfsetispeed(&tty, B115200);
    
    // 8N1 configuration
    tty.c_cflag &= ~PARENB;   // No parity
    tty.c_cflag &= ~CSTOPB;   // One stop bit
    tty.c_cflag &= ~CSIZE;    // Clear size bits
    tty.c_cflag |= CS8;       // 8 data bits
    
    tty.c_cflag &= ~CRTSCTS;  // No hardware flow control
    tty.c_cflag |= CREAD | CLOCAL; // Enable read, ignore modem controls
    
    // Raw input/output
    tty.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
    tty.c_iflag &= ~(IXON | IXOFF | IXANY | ICRNL);
    tty.c_oflag &= ~OPOST;
    
    // Set read timeout
    tty.c_cc[VMIN] = 0;
    tty.c_cc[VTIME] = 50; // 5 second timeout
    
    if (tcsetattr(fd, TCSANOW, &tty) != 0) {
        return -1;
    }
    
    return 0;
}

/*******************************************************************************
**
** Function         FindSerialDevice
**
** Description      Auto-detect Pico 2 W USB CDC device
**
** Parameters       device_path - buffer for device path (e.g., /dev/ttyACM0)
**                  max_path    - maximum buffer size
**
** Returns          0 on success, -1 on failure
**
*******************************************************************************/
int NfccUsbSerialTransport::FindSerialDevice(char* device_path, int max_path) {
    // Try common CDC ACM devices first
    const char* candidate_devices[] = {
        "/dev/ttyACM0",
        "/dev/ttyACM1", 
        "/dev/ttyUSB0",
        "/dev/ttyUSB1"
    };
    
    for (size_t i = 0; i < sizeof(candidate_devices) / sizeof(candidate_devices[0]); i++) {
        struct stat st;
        if (stat(candidate_devices[i], &st) == 0) {
            // Device exists, test if it's accessible
            int test_fd = open(candidate_devices[i], O_RDWR | O_NONBLOCK);
            if (test_fd >= 0) {
                close(test_fd);
                strncpy(device_path, candidate_devices[i], max_path - 1);
                device_path[max_path - 1] = '\0';
                return 0;
            }
        }
    }
    
    return -1;
}