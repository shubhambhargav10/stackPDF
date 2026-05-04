import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from PyPDF2 import PdfMerger

PARENT_FOLDER = ""


def merge_pdfs(OUTPUT_DIR, PARENT_FOLDER, stream=False):
    merger = PdfMerger()
    pdf_files = sorted([
        os.path.join(OUTPUT_DIR, f)
        for f in os.listdir(OUTPUT_DIR)
        if f.endswith(".pdf")
    ])
    if not pdf_files:
        msg = "❌ No PDFs generated. Check input folder."
        if stream:
            yield msg
            return
        else:
            raise Exception(msg)

    for pdf in pdf_files:
        merger.append(pdf)

    output_path = os.path.join(PARENT_FOLDER, "final_output.pdf")
    merger.write(output_path)
    merger.close()
    msg = f"🎉 Final PDF created: {output_path}"
    print(msg)
    if stream:
        yield msg
        return
    else:
        return output_path


def detect_package_type(PARENT_FOLDER):
    """
    Returns:
      ("edetailer", [sorted subfolder names])  — subfolders contain HTML files
      ("email",     [sorted .html filenames])   — HTML files sit flat at root
      ("unknown",   [])
    """
    all_items = os.listdir(PARENT_FOLDER)

    subfolders = [
        item for item in all_items
        if os.path.isdir(os.path.join(PARENT_FOLDER, item))
        and item != "temp_pdf"
        and not item.startswith(".")
    ]

    subfolders_with_html = [
        sf for sf in subfolders
        if any(
            f.endswith(".html") and not f.startswith("._")
            for f in os.listdir(os.path.join(PARENT_FOLDER, sf))
        )
    ]

    root_html = [
        item for item in all_items
        if item.endswith(".html")
        and not item.startswith("._")
        and os.path.isfile(os.path.join(PARENT_FOLDER, item))
    ]

    if subfolders_with_html:
        return ("edetailer", sorted(subfolders_with_html))
    elif root_html:
        return ("email", sorted(root_html))
    else:
        return ("unknown", [])


def generate_pdf(PARENT_FOLDER, stream=False):
    if not os.path.exists(PARENT_FOLDER):
        msg = f"❌ Invalid folder path: {PARENT_FOLDER}"
        print(msg)
        if stream:
            yield msg
            return
        else:
            raise Exception(msg)
    if not os.path.isdir(PARENT_FOLDER):
        msg = f"❌ Not a folder: {PARENT_FOLDER}"
        if stream:
            yield msg
            return
        else:
            raise Exception(msg)

    OUTPUT_DIR = os.path.join(PARENT_FOLDER, "temp_pdf")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    CONFIG_PATH = os.path.join(PARENT_FOLDER, "config.json")
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        print("✅ Using project config")
    else:
        print("⚠️ No config found")

    # ── Detect package type ──
    package_type, items = detect_package_type(PARENT_FOLDER)
    print(f"📦 Package type: {package_type} | items: {items}")

    if package_type == "unknown":
        msg = "❌ No HTML files found. Make sure your zip contains .html files."
        if stream:
            yield msg
            return
        else:
            raise Exception(msg)

    msg = f"📦 Detected: {package_type.upper()} ({len(items)} item(s))"
    print(msg)
    if stream:
        yield msg

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ════════════════════════════════════════════════════════
        # PATH A — eDETAILER  (original logic, completely untouched)
        # ════════════════════════════════════════════════════════
        if package_type == "edetailer":
            page = browser.new_page()
            page.set_viewport_size({"width": 1366, "height": 1024})

            folders = items
            print("Folders found:", folders)

            for folder in folders:
                print(f"\n--- START {folder} ---")
                folder_path = os.path.join(PARENT_FOLDER, folder)

                print("Listing files...")
                files = os.listdir(folder_path)
                print("Files found:", files)

                html_files = []
                for htmfile in os.listdir(folder_path):
                    if htmfile.endswith(".html"):
                        html_files.append(htmfile)
                        print("HTML files:", html_files)

                if not html_files:
                    print("⚠️ No HTML file found in", folder)
                    msg = f"⚠️ No HTML file found in {folder}"
                    if stream:
                        yield msg
                    else:
                        print(msg)
                    continue

                html_path = os.path.join(folder_path, html_files[0])
                print("Using HTML file:", html_path)

                file_url = Path(html_path).absolute().as_uri()
                print("File URL:", file_url)

                msg = f"📂 Processing {folder}"
                if stream:
                    yield msg

                states = config.get(folder, [{"type": "base"}])
                print(f"States {states}")

                state_index = 0

                for state in states:
                    page.goto(file_url)
                    page.evaluate("""
                        () => {
                            document.body.style.width = '1366px';
                            document.body.style.height = '1024px';
                            document.body.style.overflow = 'hidden';
                            document.body.style.transform = 'translateY(0)';
                        }
                    """)

                    page.wait_for_timeout(1000)

                    if state.get("type") == "action":
                        for step in state.get("steps", []):
                            try:
                                if step["action"] == "click":
                                    page.wait_for_selector(step["selector"])
                                    page.click(step["selector"])
                                elif step["action"] == "wait":
                                    page.wait_for_timeout(step["time"])
                                elif step["action"] == "waitFor":
                                    page.wait_for_selector(step["selector"])
                                elif step["action"] == "scroll":
                                    page.evaluate("""
                                        (y) => {
                                            if (window.myScroll) {
                                                window.myScroll.scrollTo(0, -y, 0);
                                            }
                                        }
                                    """, step["y"])
                                    page.wait_for_timeout(300)
                            except Exception as e:
                                print("⚠️ Error:", e)

                    pdf_path = os.path.join(OUTPUT_DIR, f"{folder}_{state_index}.pdf")
                    page.pdf(
                        path=pdf_path,
                        print_background=True,
                        width="1366px",
                        height="1024px"
                    )
                    msg = f"✅ Saved {folder}_{state_index}.pdf"
                    print(msg)
                    if stream:
                        yield msg

                    state_index += 1

        # ════════════════════════════════════════════════════════
        # PATH B — EMAIL
        # Two separate PDFs: desktop (600px) and mobile (360px)
        # Each saved as its own final PDF — not merged together
        # ════════════════════════════════════════════════════════
        elif package_type == "email":
            views = [
                ("desktop", 600),
                ("mobile",  360),
            ]

            for idx, html_file in enumerate(items):
                html_path = os.path.join(PARENT_FOLDER, html_file)
                file_url  = Path(html_path).absolute().as_uri()

                msg = f"📧 Processing email: {html_file}"
                print(msg)
                if stream:
                    yield msg

                for view_name, viewport_width in views:
                    msg = f"   ↳ Rendering {view_name} view ({viewport_width}px)…"
                    print(msg)
                    if stream:
                        yield msg

                    # Fresh page per view so viewport + media queries are clean
                    page = browser.new_page()

                    # emulate_media("screen") is the key fix:
                    # Playwright defaults to "print" media when generating PDFs,
                    # which means @media (max-width: 480px) screen rules never fire.
                    # Forcing "screen" makes the email's responsive CSS actually work.
                    page.emulate_media(media="screen")

                    page.set_viewport_size({"width": viewport_width, "height": 1024})

                    # networkidle = wait for all remote images to finish loading
                    page.goto(file_url, wait_until="networkidle")

                    # Set width explicitly so table-based email layouts
                    # (which often ignore viewport) also respond correctly
                    page.evaluate(f"""
                        () => {{
                            document.documentElement.style.width = '{viewport_width}px';
                            document.body.style.width            = '{viewport_width}px';
                            document.body.style.margin           = '0';
                            document.body.style.padding          = '0';
                        }}
                    """)

                    # Give fonts + lazy images time to settle after width change
                    page.wait_for_timeout(2000)

                    # Measure the full scroll height so the PDF is exactly
                    # one tall page — no clipping, no blank overflow page
                    full_height = page.evaluate(
                        "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
                    )
                    pdf_height = f"{max(full_height, 100)}px"

                    pdf_filename = f"email_{idx:02d}_{view_name}.pdf"
                    pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

                    page.pdf(
                        path=pdf_path,
                        print_background=True,
                        width=f"{viewport_width}px",
                        height=pdf_height,
                    )

                    page.close()

                    msg = f"✅ Saved {pdf_filename}"
                    print(msg)
                    if stream:
                        yield msg

        browser.close()

    # ── For eDetailer: merge all pages into one final PDF as before ──
    # ── For email: merge produces final_output.pdf with desktop then mobile ──
    # ── (two separate downloads handled by the /download route per view) ──
    if stream:
        for msg in merge_pdfs(OUTPUT_DIR, PARENT_FOLDER, stream=True):
            yield msg
        return
    else:
        return merge_pdfs(OUTPUT_DIR, PARENT_FOLDER)
