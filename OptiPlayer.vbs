Option Explicit
Dim shell, fso, base, args, i, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
command = """" & base & "\.venv\Scripts\pythonw.exe"" """ & base & "\app.py"""
For i = 0 To WScript.Arguments.Count - 1
    command = command & " """ & Replace(WScript.Arguments(i), """", """""") & """"
Next
shell.CurrentDirectory = base
shell.Run command, 0, False
