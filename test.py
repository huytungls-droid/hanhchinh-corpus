from datetime import datetime
from pathlib import Path

out_dir = Path("output")
out_dir.mkdir(exist_ok=True)

content = f"""
HỆ THỐNG THU THẬP VĂN BẢN HÀNH CHÍNH

GitHub Actions đã chạy thành công.

Thời gian chạy:
{datetime.now().isoformat()}

Các nguồn dự kiến:
- Lạng Sơn
- Bắc Ninh
- Thái Nguyên
- Đắk Lắk

Cấp thu thập:
- Cấp tỉnh
- Xã/phường
"""

with open(
    out_dir / "kiem_tra.txt",
    "w",
    encoding="utf-8"
) as f:
    f.write(content)

print("Đã tạo output/kiem_tra.txt")
