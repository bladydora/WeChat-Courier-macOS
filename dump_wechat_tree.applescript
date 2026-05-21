-- Diagnostic helper: dump a bounded WeChat accessibility tree.
-- It prints role/name/value/position/size so we can find stable controls.

property maxDepth : 6
property maxChildren : 80

tell application "System Events"
  set candidateNames to {"WeChat", "微信"}
  repeat with procName in candidateNames
    if exists process (procName as text) then
      tell process (procName as text)
        set frontmost to true
        delay 0.2
        try
          set output to "PROCESS=" & (procName as text) & linefeed
          set output to output & my dumpElement(front window, 0)
          return output
        on error errMsg
          return "PROCESS=" & (procName as text) & linefeed & "ERROR=" & errMsg
        end try
      end tell
    end if
  end repeat
end tell

return "No visible WeChat process found."

on indentText(depth)
  set s to ""
  repeat depth times
    set s to s & "  "
  end repeat
  return s
end indentText

on safeText(prefix, itemValue)
  try
    if itemValue is missing value then
      return ""
    end if
    return " " & prefix & "=" & (itemValue as text)
  on error
    return ""
  end try
end safeText

on dumpElement(el, depth)
  if depth > maxDepth then return ""
  tell application "System Events"
    set lineText to my indentText(depth)
    try
      set lineText to lineText & role of el
    on error
      set lineText to lineText & "?"
    end try
    try
      set lineText to lineText & my safeText("name", name of el)
    end try
    try
      set lineText to lineText & my safeText("value", value of el)
    end try
    try
      set itemPosition to position of el
      set lineText to lineText & " pos={" & (item 1 of itemPosition as integer) & "," & (item 2 of itemPosition as integer) & "}"
    end try
    try
      set itemSize to size of el
      set lineText to lineText & " size={" & (item 1 of itemSize as integer) & "," & (item 2 of itemSize as integer) & "}"
    end try
    set output to lineText & linefeed
    if depth = maxDepth then return output
    try
      set childItems to UI elements of el
      set childCount to count of childItems
      if childCount > maxChildren then set childCount to maxChildren
      repeat with i from 1 to childCount
        set output to output & my dumpElement(item i of childItems, depth + 1)
      end repeat
    end try
    return output
  end tell
end dumpElement
