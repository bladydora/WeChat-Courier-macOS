import Foundation
import AppKit

if CommandLine.arguments.count < 2 {
    fputs("Usage: swift copy_files_to_clipboard.swift /path/file [more files...]\n", stderr)
    exit(2)
}

let urls = CommandLine.arguments.dropFirst().map { URL(fileURLWithPath: $0) }
let pasteboard = NSPasteboard.general
pasteboard.clearContents()

let ok = pasteboard.writeObjects(urls as [NSURL])
if !ok {
    fputs("Failed to write file URLs to pasteboard\n", stderr)
    exit(1)
}

