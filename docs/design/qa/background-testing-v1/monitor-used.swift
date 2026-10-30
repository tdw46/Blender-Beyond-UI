import AppKit
import Foundation

let args = CommandLine.arguments
let output = args[1]
let child = Process()
child.executableURL = URL(fileURLWithPath: args[2])
child.arguments = Array(args.dropFirst(3))
var events: [[String: Any]] = []
var samples = Set<Int32>()
let start = Date()
func record(_ app: NSRunningApplication?, _ kind: String) {
    guard let app = app else { return }
    events.append(["kind": kind, "pid": app.processIdentifier,
                   "bundle": app.bundleIdentifier ?? "", "seconds": Date().timeIntervalSince(start)])
}
record(NSWorkspace.shared.frontmostApplication, "initial")
let observer = NSWorkspace.shared.notificationCenter.addObserver(
    forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main
) { notification in
    record(notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication, "activation")
}
let timer = Timer.scheduledTimer(withTimeInterval: 0.01, repeats: true) { _ in
    if let app = NSWorkspace.shared.frontmostApplication { samples.insert(app.processIdentifier) }
}
try child.run()
while child.isRunning { RunLoop.current.run(until: Date().addingTimeInterval(0.02)) }
child.waitUntilExit()
RunLoop.current.run(until: Date().addingTimeInterval(0.1))
record(NSWorkspace.shared.frontmostApplication, "final")
timer.invalidate()
NSWorkspace.shared.notificationCenter.removeObserver(observer)
let data: [String: Any] = ["events": events, "sampled_frontmost_pids": Array(samples).sorted(),
                         "child_exit": child.terminationStatus, "seconds": Date().timeIntervalSince(start)]
try JSONSerialization.data(withJSONObject: data, options: [.prettyPrinted, .sortedKeys]).write(to: URL(fileURLWithPath: output))
exit(child.terminationStatus)
