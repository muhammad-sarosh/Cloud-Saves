envName = "windows_env"  ' change if needed

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' projectDir = parent of Autostart (i.e. two levels up for Autostart\Windows)
parentDir = fso.GetParentFolderName(scriptDir)
projectDir = fso.GetParentFolderName(parentDir)
If projectDir = "" Then
  projectDir = scriptDir ' fallback
End If

pyw = fso.BuildPath(projectDir, envName & "\Scripts\pythonw.exe")
autoPy = fso.BuildPath(projectDir, "auto.py")

If Not fso.FileExists(pyw) Then
  WScript.Echo "pythonw.exe not found at: " & pyw
  WScript.Quit 1
End If

Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = projectDir
' 0 = hidden, False = don't wait
sh.Run """" & pyw & """ """ & autoPy & """", 0, False
