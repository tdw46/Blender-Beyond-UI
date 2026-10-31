// Test-only LaunchServices launch. Never attaches to an existing Blender.
// Observe activation only; never restore or deliberately change application focus.
import AppKit
import Foundation

let args = CommandLine.arguments
guard args.count == 2 else { exit(2) }
let input = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[1]))) as! [String: Any]
let command = input["command"] as! [String]
let reportPath = input["report"] as! String
let url = URL(fileURLWithPath: command[0]).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
let config = NSWorkspace.OpenConfiguration()
config.activates = false
config.createsNewApplicationInstance = true
config.addsToRecentItems = false
config.promptsUserIfNeeded = false
config.arguments = Array(command.dropFirst())
config.environment = ProcessInfo.processInfo.environment
var owned: NSRunningApplication?
let initialPID = NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0
let start = Date()
var ready = false
var errorText: String?
var events: [[String: Any]] = []

let observer = NSWorkspace.shared.notificationCenter.addObserver(
    forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main
) { notification in
    guard let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else { return }
    events.append(["kind": "activation", "pid": app.processIdentifier,
                   "bundle": app.bundleIdentifier ?? "", "seconds": Date().timeIntervalSince(start)])
}
NSWorkspace.shared.openApplication(at: url, configuration: config) { app, error in
    owned = app
    errorText = error?.localizedDescription
    ready = true
}
while !ready && Date().timeIntervalSince(start) < 20 {
    RunLoop.current.run(until: Date().addingTimeInterval(0.01))
}
var timedOut = false
while let app = owned, !app.isTerminated {
    if Date().timeIntervalSince(start) > 85 {
        timedOut = true
        app.forceTerminate()
        break
    }
    RunLoop.current.run(until: Date().addingTimeInterval(0.01))
}
NSWorkspace.shared.notificationCenter.removeObserver(observer)
let report: [String: Any] = ["pid": owned?.processIdentifier ?? 0,
    "initial_frontmost_pid": initialPID,
    "final_frontmost_pid": NSWorkspace.shared.frontmostApplication?.processIdentifier ?? 0,
    "activates": false, "new_instance": true, "restore_requests": 0,
    "events": events, "timeout": timedOut, "error": errorText ?? "",
    "seconds": Date().timeIntervalSince(start)]
try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: URL(fileURLWithPath: reportPath))
exit(owned == nil || errorText != nil || timedOut ? 1 : 0)
