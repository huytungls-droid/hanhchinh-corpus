import os
import re
import json
import hashlib
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

BASE_URL = "https://daklak.gov.vn"
LIST_URL = "https://daklak.gov.vn/van-ban-chi-dao-dieu-hanh"

OUT_DIR = Path("corpus/daklak/tinh")
PDF_DIR = OUT_DIR / "pdf"
TXT_DIR = OUT_DIR / "txt"
META_DIR = OUT_DIR / "metadata"

MAX_DOCUMENTS = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/154 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)

PDF_DIR.mkdir(parents=True, exist_ok=True)
TXT_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)


def safe_name(text):
    text = text.strip().lower()
    text = re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")[:120]


def download(url):
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        return r
    except Exception as e:
        print("LỖI tải:", url, e)
        return None


def pdf_to_text(pdf_path):
    try:
        reader = PdfReader(str(pdf_path))

        parts = []

        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    parts.append(text)
            except Exception:
                pass

        return "\n".join(parts).strip()

    except Exception as e:
        print("LỖI đọc PDF:", pdf_path, e)
        return ""


def extract_pdf_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if not href:
            continue

        full_url = urljoin(page_url, href)

        if ".pdf" in full_url.lower():
            links.append(full_url)

    return list(dict.fromkeys(links))


def extract_detail_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if not href:
            continue

        full_url = urljoin(page_url, href)

        low = full_url.lower()

        if "van-ban" in low or "chi-dao" in low:
            if "daklak.gov.vn" in low:
                links.append(full_url)

    return list(dict.fromkeys(links))


def save_document(pdf_url, source_page, index):

    digest = hashlib.sha256(
        pdf_url.encode("utf-8")
    ).hexdigest()[:16]

    filename = f"{index:04d}_{digest}"

    pdf_path = PDF_DIR / f"{filename}.pdf"
    txt_path = TXT_DIR / f"{filename}.txt"
    meta_path = META_DIR / f"{filename}.json"

    if txt_path.exists():
        print("Đã có:", txt_path.name)
        return True

    print()
    print("Tải PDF:")
    print(pdf_url)

    r = download(pdf_url)

    if not r:
        return False

    content_type = r.headers.get(
        "content-type",
        ""
    ).lower()

    if (
        "pdf" not in content_type
        and not pdf_url.lower().endswith(".pdf")
    ):
        print("Không phải PDF")
        return False

    pdf_path.write_bytes(r.content)

    text = pdf_to_text(pdf_path)

    if len(text) < 100:
        print(
            "PDF không có đủ text:",
            len(text),
            "ký tự"
        )
        return False

    txt_path.write_text(
        text,
        encoding="utf-8"
    )

    metadata = {
        "province": "Đắk Lắk",
        "level": "tỉnh",
        "source_page": source_page,
        "file_url": pdf_url,
        "characters": len(text),
        "pdf_file": str(pdf_path),
        "txt_file": str(txt_path),
    }

    meta_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        "OK:",
        txt_path.name,
        "|",
        len(text),
        "ký tự"
    )

    return True


def main():

    print("=" * 70)
    print("THỬ NGHIỆM THU THẬP VĂN BẢN ĐẮK LẮK")
    print("=" * 70)

    print("Đang mở:")
    print(LIST_URL)

    r = download(LIST_URL)

    if not r:
        raise SystemExit(
            "Không mở được trang Đắk Lắk"
        )

    detail_links = extract_detail_links(
        r.text,
        LIST_URL
    )

    print(
        "Tìm thấy",
        len(detail_links),
        "link ứng viên"
    )

    all_pdf_links = []

    # Tìm PDF ngay trên trang danh sách
    direct_pdfs = extract_pdf_links(
        r.text,
        LIST_URL
    )

    for pdf in direct_pdfs:
        all_pdf_links.append(
            (pdf, LIST_URL)
        )

    # Chỉ duyệt số lượng trang vừa phải trong lần test đầu
    for i, detail_url in enumerate(
        detail_links[:100],
        start=1
    ):

        print(
            f"[Trang {i}/{min(100, len(detail_links))}]",
            detail_url
        )

        rr = download(detail_url)

        if not rr:
            continue

        pdfs = extract_pdf_links(
            rr.text,
            detail_url
        )

        for pdf in pdfs:
            all_pdf_links.append(
                (pdf, detail_url)
            )

        if len(all_pdf_links) >= MAX_DOCUMENTS * 2:
            break

    # loại trùng URL
    unique = []
    seen = set()

    for pdf_url, page_url in all_pdf_links:

        if pdf_url in seen:
            continue

        seen.add(pdf_url)
        unique.append(
            (pdf_url, page_url)
        )

    print()
    print(
        "Tổng PDF ứng viên:",
        len(unique)
    )

    success = 0

    for pdf_url, source_page in unique:

        if success >= MAX_DOCUMENTS:
            break

        ok = save_document(
            pdf_url,
            source_page,
            success + 1
        )

        if ok:
            success += 1

    print()
    print("=" * 70)
    print("HOÀN TẤT THỬ NGHIỆM")
    print("TXT lấy được:", success)
    print("=" * 70)

    if success == 0:
        raise SystemExit(
            "Không lấy được văn bản nào."
        )


if __name__ == "__main__":
    main()
