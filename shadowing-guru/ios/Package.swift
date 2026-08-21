// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ShadowingGuru",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "ShadowingGuruDomain", targets: ["ShadowingGuruDomain"]),
        .library(name: "ShadowingGuruUI", targets: ["ShadowingGuruUI"]),
    ],
    targets: [
        .target(
            name: "ShadowingGuruDomain",
            resources: [.copy("Resources/cmudict.txt")]
        ),
        .target(
            name: "ShadowingGuruUI",
            dependencies: ["ShadowingGuruDomain"],
            resources: [.copy("Resources/samples.json")]
        ),
        .testTarget(
            name: "ShadowingGuruDomainTests",
            dependencies: ["ShadowingGuruDomain"],
            resources: [.copy("Resources/golden.json")]
        ),
        .testTarget(
            name: "ShadowingGuruUITests",
            dependencies: ["ShadowingGuruUI", "ShadowingGuruDomain"]
        ),
    ]
)
