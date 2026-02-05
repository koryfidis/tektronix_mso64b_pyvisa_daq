# tektronix_mso64b_pyvisa_daq
Tektronix MSO64B Oscilloscope DAQ &amp; Automation. A Python-based utility for automated waveform acquisition, triggering, and bulk CSV data transfer from Tektronix 4/5/6 Series scopes to a local PC using PyVISA and PyUSB.

# Tektronix DAQ & Automation Suite

This repository provides a robust Python implementation for automating Data Acquisition (DAQ) on Tektronix oscilloscopes. It handles the end-to-end process: establishing a stable connection, configuring horizontal/vertical parameters, managing triggers, and syncing data files to a local machine.

## Key Features
* **Handshake & Flush:** Implements a buffer clearing routine to prevent the common "Connected: 1" sync errors over USB.
* **Sequence Acquisition:** Automates Sequence mode captures for high-speed event recording.
* **Save-on-Trigger:** Configures the instrument to automatically save waveforms to its internal drive (`C:/Silicon`) upon trigger.
* **Efficient File Transfer:** Uses `read_raw()` streams to pull `.csv` files from the scope's filesystem to a local directory.

## Prerequisites

### Software Requirements
This script is designed to run using the `pyvisa-py` backend, which is a lightweight alternative to NI-VISA or Keysight IO Libraries.

```bash
pip install pyvisa pyvisa-py pyusb
