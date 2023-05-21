import wmi
import os
import time

f = wmi.WMI()
print("Find all the SQL processes and kill them")
for process in f.Win32_Process():
    if "sql" in process.Name:
        print(process.Name)
        os.system(f"taskkill /IM {process.Name} /F")

print("Done")
time.sleep(1)
