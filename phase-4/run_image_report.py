import json
import sys
import time

from image_extractor import extract_report_text
from processor import process_report


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python run_image_report.py <image_path>"
        )
        sys.exit(1)

    image_path = sys.argv[1]

    print("=" * 70)
    print("PHASE 5 - LAB REPORT IMAGE TEST")
    print("=" * 70)

    print(f"Input image: {image_path}")

    start_time = time.perf_counter()

    try:
        print("\n[1/2] Extracting report text from image...")

        extracted_text = extract_report_text(image_path)

        print("\n--- EXTRACTED REPORT TEXT ---")
        print(extracted_text)
        print("--- END EXTRACTED TEXT ---")

        print("\n[2/2] Running Phase 4 processor...")

        result = process_report(extracted_text)

        elapsed = time.perf_counter() - start_time

        print("\n--- PROCESSING RESULT ---")
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

        print(
            f"\nTotal processing time: {elapsed:.2f} seconds"
        )

    except Exception as exc:
        elapsed = time.perf_counter() - start_time

        print(
            f"\n[ERROR] Processing failed after "
            f"{elapsed:.2f} seconds"
        )

        print(
            f"[ERROR] {type(exc).__name__}: {exc}"
        )

        sys.exit(1)


if __name__ == "__main__":
    main()