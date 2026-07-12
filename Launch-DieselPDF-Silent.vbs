Set shell = CreateObject("WScript.Shell")
app = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\DieselPDF.pyw"
pythonw = "C:\Users\AaronHan\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
shell.Run """" & pythonw & """ """ & app & """", 1, False
