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

#pragma once
#include <NfccTransport.h>

class NfccUsbSerialTransport : public NfccTransport {
public:
  /*****************************************************************************
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
   ****************************************************************************/
  NFCSTATUS OpenAndConfigure(pphTmlNfc_Config_t pConfig, void** pLinkHandle) override;

  /*****************************************************************************
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
   ****************************************************************************/
  int Read(void* pDevHandle, uint8_t* pBuffer, int nNbBytesToRead) override;

  /*****************************************************************************
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
   ****************************************************************************/
  int Write(void* pDevHandle, uint8_t* pBuffer, int nNbBytesToWrite) override;

  /*****************************************************************************
   **
   ** Function         Close
   **
   ** Description      Closes USB serial bridge connection
   **
   ** Parameters       pDevHandle - device handle
   **
   ** Returns          None
   **
   ****************************************************************************/
  void Close(void* pDevHandle) override;

  /*****************************************************************************
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
   ****************************************************************************/
  int NfccReset(void* pDevHandle, NfccResetType eType) override;

  /*****************************************************************************
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
  int GetIrqState(void* pDevHandle) override;

private:
  /*****************************************************************************
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
   ****************************************************************************/
  int SendCommand(int fd, const char* command, char* response, int max_response);

  /*****************************************************************************
   **
   ** Function         SetupSerial
   **
   ** Description      Configure serial port parameters
   **
   ** Parameters       fd - serial device file descriptor
   **
   ** Returns          0 on success, -1 on failure
   **
   ****************************************************************************/
  int SetupSerial(int fd);

  /*****************************************************************************
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
   ****************************************************************************/
  int FindSerialDevice(char* device_path, int max_path);

  // Private members
  int m_serial_fd;
  bool m_fw_dwnld_mode;
  char m_device_path[256];
};