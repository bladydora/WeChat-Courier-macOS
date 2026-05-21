import Foundation
import Vision
import AppKit
import ImageIO

if CommandLine.arguments.count < 2 {
    fputs("Usage: swift ocr_boxes.swift /path/to/image.png\n", stderr)
    exit(2)
}

let imagePath = CommandLine.arguments[1]
let imageURL = URL(fileURLWithPath: imagePath)

guard let imageSource = CGImageSourceCreateWithURL(imageURL as CFURL, nil),
      let cgImage = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) else {
    fputs("Failed to load image: \(imagePath)\n", stderr)
    exit(2)
}

let request = VNRecognizeTextRequest { request, error in
    if let error = error {
        fputs("OCR error: \(error.localizedDescription)\n", stderr)
        exit(1)
    }

    guard let observations = request.results as? [VNRecognizedTextObservation] else {
        return
    }

    for observation in observations {
        guard let text = observation.topCandidates(1).first else {
            continue
        }
        let box = observation.boundingBox
        let safeText = text.string
            .replacingOccurrences(of: "\t", with: " ")
            .replacingOccurrences(of: "\n", with: " ")
        print("\(safeText)\t\(box.minX)\t\(box.minY)\t\(box.width)\t\(box.height)")
    }
}

request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "en-US"]

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([request])
} catch {
    fputs("OCR perform failed: \(error.localizedDescription)\n", stderr)
    exit(1)
}
