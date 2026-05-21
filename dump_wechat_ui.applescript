-- Diagnostic helper.
-- Run this from the same terminal/SSH session that triggers WeChat automation.
-- It tries common macOS WeChat process names and prints visible UI names.

tell application "System Events"
  set candidateNames to {"WeChat", "微信"}
  repeat with procName in candidateNames
    if exists process (procName as text) then
      tell process (procName as text)
        set frontmost to true
        delay 0.2
        try
          return "PROCESS=" & (procName as text) & linefeed & my dumpNames(front window)
        on error errMsg
          return "PROCESS=" & (procName as text) & linefeed & "ERROR=" & errMsg
        end try
      end tell
    end if
  end repeat
end tell

return "No visible WeChat process found."

on dumpNames(rootElement)
  tell application "System Events"
    set output to ""
    try
      set output to output & "WINDOW_NAME=" & (name of rootElement as text) & linefeed
    end try
    try
      set elementNames to name of every UI element of rootElement
      repeat with itemName in elementNames
        try
          set output to output & (itemName as text) & linefeed
        end try
      end repeat
    end try
    return output
  end tell
end dumpNames
