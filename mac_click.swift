import ApplicationServices
import Foundation

if CommandLine.arguments.count != 3 {
    fputs("usage: mac_click.swift X Y\n", stderr)
    exit(2)
}

guard
    let x = Double(CommandLine.arguments[1]),
    let y = Double(CommandLine.arguments[2])
else {
    fputs("X and Y must be numbers\n", stderr)
    exit(2)
}

let point = CGPoint(x: x, y: y)
let source = CGEventSource(stateID: .hidSystemState)

guard
    let down = CGEvent(
        mouseEventSource: source,
        mouseType: .leftMouseDown,
        mouseCursorPosition: point,
        mouseButton: .left
    ),
    let up = CGEvent(
        mouseEventSource: source,
        mouseType: .leftMouseUp,
        mouseCursorPosition: point,
        mouseButton: .left
    )
else {
    fputs("failed to create mouse event\n", stderr)
    exit(1)
}

down.post(tap: .cghidEventTap)
usleep(80_000)
up.post(tap: .cghidEventTap)
