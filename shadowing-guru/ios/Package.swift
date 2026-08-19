// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ShadowingGuruDomain",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "ShadowingGuruDomain", targets: ["ShadowingGuruDomain"]),
    ],
    targets: [
        .target(
            name: "ShadowingGuruDomain",
            resources: [.copy("Resources/cmudict.txt")]
        ),
        .testTarget(
            name: "ShadowingGuruDomainTests",
            dependencies: ["ShadowingGuruDomain"],
            resources: [.copy("Resources/golden.json")]
        ),
    ]
)
