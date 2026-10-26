Echo "Remove CLIB log"
del C:\CLIB\Data\CLIB_log.ldf

Echo "Pull GIT repository"
cd c:\clib\libServer
git pull origin
copy keyInput.txt keyInput.py

Echo "Download Datebase"
Echo "Assume that checkout/return happens only in this system"
python3 downloadDb.py

Echo "Start CLIB Web server"
Start-Process -FilePath "c:\clib\libServer\server\run.bat" -WorkingDirectory "c:\clib\libServer\server" -WindowStyle Minimized

Echo "Open CLIB page"
# Wait for the server to answer (the first run also installs its packages)
$clibUrl = "http://127.0.0.1:8080/"
$clibSelfUrl = "http://127.0.0.1:8081/"
$deadline = (Get-Date).AddMinutes(5)
while ((Get-Date) -lt $deadline) {
  try {
    Invoke-WebRequest -Uri $clibUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
    break
  }
  catch {
    Start-Sleep -Seconds 2
  }
}
# Through explorer so the browser doesn't inherit admin rights if the task runs elevated
explorer.exe $clibUrl
explorer.exe $clibSelfUrl
