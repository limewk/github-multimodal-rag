Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptsDir = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(scriptsDir)
ui = fso.BuildPath(root, "ui")
logs = fso.BuildPath(root, "logs")
If Not fso.FolderExists(logs) Then
  fso.CreateFolder(logs)
End If

backend = "cmd /k cd /d """ & root & """ && "".venv\Scripts\python.exe"" -m uvicorn src.api.main:app --host 127.0.0.1 --port 8002 > ""logs\backend.out.log"" 2> ""logs\backend.err.log"""
frontend = "cmd /k cd /d """ & ui & """ && ""node_modules\.bin\vite.cmd"" --host 127.0.0.1 --port 3000 > ""..\logs\frontend.out.log"" 2> ""..\logs\frontend.err.log"""

shell.Run backend, 0, False
shell.Run frontend, 0, False
