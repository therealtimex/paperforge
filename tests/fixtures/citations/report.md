+++
abstract = "Kiểm thử trích dẫn, công thức và siêu dữ liệu tác giả trên nguồn thực tế."
keywords = ["Physical AI", "Việt Nam", "chính sách công nghệ"]

[[author]]
name = "Nhóm Nghiên cứu Paperforge"
affiliation = [1]
orcid = "0000-0002-1825-0097"
corresponding = true
email = "research@example.vn"

[affiliation]
1 = "Paperforge"

[declarations]
funding = "Không có nguồn tài trợ ngoài."
conflicts = "Không có xung đột lợi ích."
+++

# BÁO CÁO NGHIÊN CỨU CHÍNH SÁCH
## Kiểm thử trích dẫn với nguồn thực tế

---
**Cơ quan thực hiện:** Paperforge
**Thời gian hoàn thành:** Tháng 08/2026

---

## MỤC LỤC

1. **Bối cảnh**
2. **Phương pháp**
3. **Nguồn dẫn**

---

## Bối cảnh {.part}

Nghị quyết 57 xác lập định hướng đột phá [@nq57], và Quyết định 21 ban hành danh
mục 10 nhóm công nghệ chiến lược [@qd21]. Chương trình học bổng tinh hoa được
phê duyệt cùng năm [@qd1600].

## Phương pháp {.part}

Đóng góp của năng suất các nhân tố tổng hợp được tính theo @eq-solow (phần dư
Solow), trong
đó $alpha$ là tỷ trọng vốn và $"TFP"$ là phần còn lại sau khi trừ đóng góp của
vốn và lao động:

$$
"TFP" = g_Y - alpha g_K - (1 - alpha) g_L
$$ {#eq-solow}

Đóng góp của phần dư vào tăng trưởng được viết là @eq-share. Đoạn văn này nằm
giữa hai công thức có nhãn, và đó là lý do nó tồn tại: trước khi hàng rào đóng
mang nhãn được nhận diện, mọi dòng ở đây bị bỏ qua và cổng kiểm tra nội dung
lặng lẽ ngừng đọc phần còn lại của tài liệu.

$$
s_A = g_A \/ g_Y
$$ {#eq-share}

Tỷ lệ tập trung tinh luyện được lấy trung bình theo trọng số sản lượng,
$sum_(i=1)^n w_i c_i$, với $w_i = q_i \/ sum_j q_j$. Ngưỡng cảnh báo đặt tại
$c >= 0.6$; các giá trị trong khoảng $0.4 <= c < 0.6$ được xem là rủi ro trung
bình. Chi phí biên của việc mở rộng công suất ước tính theo $(dif C)\/(dif q)$.

Các mức giá trong báo cáo được ghi bằng USD; ví dụ $5 và $10 là văn xuôi chứ
không phải công thức, và phải hiện ra đúng như vậy.

## Nguồn dẫn {.part}

Trữ lượng đất hiếm tham chiếu theo USGS [@usgs2026]; tiềm năng điện gió ngoài
khơi theo Ngân hàng Thế giới [@esmap; @wipo].

Bảy cột không nằm vừa một cột báo: @tbl-nguon phải rời khỏi cột và lấy cạnh dài
của khổ giấy, ở cả ba bản.

| Quốc gia | Mật độ 2025 | Chỉ số lương | Công cụ | Từ năm | Trần hỗ trợ | Nguồn |
|:---|---:|---:|:---|---:|:---|:---|
| Hàn Quốc | ~1012 | 100 | Tín dụng thuế | 2013 | Không | https://ifr.org/statistics/korea-2025 |
| Singapore | 770 | 96 | Tài trợ | 2016 | 50% vốn đầu tư | https://ifr.org/statistics/singapore-2025 |
| Việt Nam | 28 | 22 | Chưa có | – | – | https://ifr.org/statistics/vietnam-2025 |

: Công cụ chính sách đang hiệu lực, một số nền kinh tế {#tbl-nguon}
