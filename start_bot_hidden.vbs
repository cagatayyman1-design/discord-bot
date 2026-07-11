Set WshShell = CreateObject("WScript.Shell")
' 0 means hidden window
WshShell.Run chr(34) & "bot_loop.bat" & Chr(34), 0
Set WshShell = Nothing
