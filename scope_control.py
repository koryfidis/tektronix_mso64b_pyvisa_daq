import pyvisa
import os
import time

RESOURCE = "USB0::1689::1328::C047065::0::INSTR" #scope address
SCOPE_INTERNAL_DIR = "C:/Silicon"               #scope directory
PC_LOCAL_DIR = "./Lab_Data_Transfer"		#computer directory for .csv final transfer

# ================================================================
# 1. 		CONNECTION (fixes "Connected: 1")
# ================================================================
def open_scope(resource):
    rm = pyvisa.ResourceManager('@py')
    scope = rm.open_resource(resource)
    
    print("Establishing clean connection...")
    scope.timeout = 500  # timeout for flushing
    
    # 1. Clear the USB buffer repeatedly until it returns a valid ID
    for i in range(5):
        try:
            scope.clear()     
            while True:       # Read junk until timeout
                scope.read()
        except:
            pass # Buffer is empty
            
        # 2. test connection as usual
        try:
            scope.write("*CLS") 
            idn = scope.query("*IDN?").strip()
            if "TEKTRONIX" in idn.upper():
                print(f"Connected: {idn}")
                break # connection ok
            else:
                print(f"   Buffer dirty (got '{idn}'), flushing again...")
                time.sleep(1)
        except:
            pass
    else:
        
        print("Warning: Scope comms might be out of sync. RETRY")

    # 3. Restore settings for work
    scope.timeout = 60000  # 60s timeout
    scope.chunk_size = 1024 * 1024 
    scope.write('*RST') 
    time.sleep(4) # timeout for reset 
    return rm, scope

# ================================================================
# 2. 		CONFIGURE (waveform presets)
# ================================================================
def configure_scope(scope):
    scope.write("ACQuire:STATE OFF") 

    # ===== CHANNELS =====
    scope.write("DISplay:WAVEView1:VIEWStyle OVERLAY") 

    # --- CH1 ---
    scope.write("DISplay:WAVEVIEW1:CH1:STATE 1") 
    scope.write("SELect:CH1 ON")   
    scope.write("DISplay:WAVEVIEW1:CH1:VERTical:POSition 4") 
    scope.write("CH1:SCAle 1")

    # --- CH2 ---
    scope.write("DISplay:WAVEVIEW1:CH2:STATE 1") 
    scope.write("SELect:CH2 ON")   
    scope.write("DISplay:WAVEVIEW1:CH2:VERTical:POSition 4") 
    scope.write("CH2:SCAle 1")

    # ===== HORIZONTAL =====
    scope.write("HORizontal:MODe MANUAL")
    scope.write("HORizontal:MODe:SCAle 400e-9")            
    scope.write("HORizontal:POSition 5") 
    scope.write("HORizontal:RECOrdlength 5000") 
    scope.write("HORizontal:MODe:SAMPLERate 1.25e9") 

    # ===== ACQUIRE MODE =====
    scope.write("ACQuire:MODe HIRES")
    scope.write("ACQuire:SEQuence:MODe") 
    scope.write("ACQuire:SEQuence:NUMSEQuence 20") 
    scope.write("ACQuire:STOPAfter SEQuence") 

# ================================================================
# 3. 			TRIGGER
# ================================================================
def set_trigger(scope):
    scope.write("TRIGger:A:MODe NORMal") 
    scope.write("TRIGger:A:TYPe EDGE") 
    scope.write("TRIGger:A:EDGE:SOUrce CH1") 
    scope.write("TRIGger:A:LEVel:CH1 -0.5") 
    scope.write("TRIGger:A:EDGE:SLOPe FALL") 

# ================================================================
# 4. 			ACT ON TRIGGER
# ================================================================
def configure_act_on_trigger(scope):
    print(f"Configuring Save-on-Trigger to {SCOPE_INTERNAL_DIR}...")
    
    # 1. Create Directory and write 
    try: scope.write(f'FILESystem:MKDir "{SCOPE_INTERNAL_DIR}"')
    except: pass
    scope.write(f'FILESystem:DELEte "{SCOPE_INTERNAL_DIR}/*"')

    # 2. Configure SAVEONEVENT
    scope.write(f'SAVEONEVent:FILEDest "{SCOPE_INTERNAL_DIR}"')
    scope.write('SAVEONEVent:FILEName "run"')
    scope.write("SAVEONEVent:WAVEform:FILEFormat SPREadsheet")
    scope.write("SAVEONEVent:WAVEform:SOUrce ALL")

    # 3. Enable Action
    scope.write("ACTONEVent:TRIGger:ACTION:SAVEWAVEform:STATE 1")
    scope.write("ACTONEVent:ENable 1")
    scope.query("*OPC?") # Sync (operations complete command)

# ================================================================
# 5. 			TRANSFER FILES
# ================================================================
def transfer_files(scope):
    target_dir = "C:/Silicon" 
    print(f"Scope Directory: {target_dir}")
    
    if not os.path.exists(PC_LOCAL_DIR):
        os.makedirs(PC_LOCAL_DIR)

    # 1.
    scope.write(f'FILESystem:CWD "{target_dir}"')
    try: scope.query("*OPC?")
    except: time.sleep(2)
    
    # 2. GET FILE LIST (The Patient Way)
    print("Reading file list (Waiting for scope response)...")
    original_timeout = scope.timeout
    scope.timeout = 10000 #tested with10000) 
    
    try:
        scope.write("FILESystem:DIR?")
        time.sleep(2.0) 
        files_str = scope.read().strip()
    except Exception as e:
        print(f"Error reading directory: {e}")
        scope.timeout = original_timeout 
        return

    scope.timeout = original_timeout

    if not files_str or files_str == '""':
        print(f"No files found in {target_dir}!")
        return

    # 3. data parcing
    clean_str = files_str.replace('"', '').replace(';', ',')
    raw_list = clean_str.split(',')       
    file_list = [f.strip() for f in raw_list if f.strip().lower().endswith(".csv")] # a startswith runX* can be put here to transfer different runs each time
    
    print(f"Found {len(file_list)} CSV files. Starting Download...")

    # 4. read_raw fixes the problem with file transfering
    for i, filename in enumerate(file_list):
        print(f"Downloading {i+1}/{len(file_list)}: {filename}")
        
        try:
            # Request file
            scope.write(f'FILESystem:READFile "{filename}"')
            
            # Read the raw bytes directly (No header parsing)
            data = scope.read_raw()
            
            # Save to PC
            with open(os.path.join(PC_LOCAL_DIR, filename), 'wb') as f:
                f.write(data)
                
        except Exception as e:
            print(f"Error transferring {filename}: {e}")
            
    print(f"Files saved in {os.path.abspath(PC_LOCAL_DIR)}")
# ================================================================
# 			MAIN
# ================================================================
if __name__ == "__main__":
    rm, scope = open_scope(RESOURCE)

    #function calling in order after establishing connection
    configure_scope(scope)
    set_trigger(scope)
    configure_act_on_trigger(scope)

    print("Starting Acquisition...")
    scope.write("ACQuire:STATE ON")

    # when acquisition stops then ask for data
    while True:
        try:
            state = int(scope.query("ACQuire:STATE?").strip())
            if state == 0: break
            time.sleep(0.5)
        except:
            pass

    print("Acquisition done.")
    


    print("Waiting 10 seconds...")
    time.sleep(10)
    
    transfer_files(scope)

    scope.close()
    rm.close()
