# Bonus report: B7

(File riêng vì `lab8.check_submission` chỉ nhận tiêu đề B1–B6 cho `bonus_report.md`; file đó đang dành cho B4.)

- Topic + nguồn (tên, năm, slide): B7, kiểm toán grader. EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* (slide 44, 59), theo `docs/bonus_topics.md`; nhóm chưa đọc bản gốc.
- CLAIM của nguồn (1 câu): theo mô tả của lab, nếu thước đo sai thì mọi so sánh shape đều sai theo, kể cả khi shape đúng.
- BOUNDARY (model / dataset / setup): chỉ kiểm hàm `summarize` trên các fixture nhỏ của giảng viên (workflow, 6 claim × 2 seed) và `lab8.compensation.quote`. Không nói gì về `trial_pass` hay grader hidden.
- HYPOTHESIS trên LogiX: có ít nhất một bản `summarize` lệch ở quan hệ hạ tầng và một bản lệch ở quan hệ nhân đôi; ngoài ra có lỗi mà ba quan hệ cho sẵn không bắt được.
- Biến cố định / biến thay đổi: cố định fixture và code `summarize`; đổi bản `summarize` (A, B, C, và `lab8.metrics.summarize` làm cột thứ tư) và quan hệ.
- Lệnh tái lập (chạy trong `src/`):

```text
python -m pytest -q tests/test_bonus_grader_audit.py
python -m bonus.grader_audit_report --out reports/bonus_grader_audit.json
```

- File report + run id: `src/reports/bonus_grader_audit.json` (sinh bằng script, không sửa tay). Code: `src/bonus/grader_relations.py`.

## Kết quả

Quan hệ độ trễ (2 so với 3 ngày, qua `quote`, không đi qua `summarize`): số tiền đổi từ 0 sang 35.000 = phí ship, quyết định lật đúng luật. Với các quan hệ còn lại, mỗi ô là "giữ" hoặc "lệch" (số metric lệch):

| Bản | Hạ tầng không đổi pass rate | Nhân đôi: tỉ lệ giữ, tổng gấp đôi | Thay 1 trial pass bằng hạ tầng: pass^5 (**quan hệ mới**) | Hoán vị thứ tự (đối chứng) |
| --- | --- | --- | --- | --- |
| `lab8.metrics.summarize` | lệch (12) | lệch (1: `pass_5`) | lệch (1) | giữ |
| grader_a | giữ | lệch (3) | lệch (1) | lệch (4) |
| grader_b | giữ | lệch (1: `pass_5`) | lệch (1) | giữ |
| grader_c | lệch (12) | lệch (1: `pass_5`) | lệch (1) | giữ |

Lỗi gọi tên theo hành vi, kèm số:

- **Bản C: đếm trial hạ tầng vào mẫu số như quyết định sai.** Gán `passed=False` cho trial `infra_error`; thêm 4 trial timeout/crash làm pass rate tụt 0.75 → 0.5625, `pass_5` 0.667 → 0.5, cost/success 21.06 → 23.72. Hàm gốc `lab8.metrics.summarize` cũng cư xử như C vì nó không đọc `infra_error`.
- **Bản A: cộng lại chi phí trial đầu tiên của mỗi claim.** Tổng cost 283.5 thay vì 189.5 trên fixture gốc, nhân đôi danh sách cho 473.0 thay vì 567.0 (cost/success 31.5 → 26.28, lẽ ra đứng yên). Hệ quả: cost phụ thuộc thứ tự trial (đảo thứ tự cho 285.0 thay vì 283.5), nên cùng dữ liệu cho hai số khác nhau.
- **Cả bốn: `pass_5` về 0 khi danh sách bị nhân đôi** (0.667 → 0.0). Nguyên nhân: điều kiện `len(claim_rows) == len(seeds)` trong `lab8.metrics.summarize`, bản A/B/C kế thừa. Benchmark thật không nhân đôi trial nên không ảnh hưởng số đã nộp. Nhóm không sửa `metrics.py`.
- **Bản B giữ cả ba quan hệ cho sẵn** (ngoài lỗi `pass_5` kế thừa ở trên), nên là bản gần đúng nhất, nhưng vẫn lệch quan hệ mới.

**Quan hệ mới: `infra_replace_keeps_pass5`.** Lấy một claim pass đủ seed, đổi một trial thành `infra_error`. Claim đó không còn bằng chứng đủ seed nên phải ra khỏi mẫu số của pass^5, giống cách trial hạ tầng đã ra khỏi mẫu số pass rate. Giá trị kỳ vọng tính độc lập (không qua `summarize`): 3/5 = 0.6. Cả bốn bản trả 0.5 vì vẫn đếm claim đó như một claim fail pass^5. Đây là lỗi mà ba quan hệ cho sẵn không bắt: B qua quan hệ hạ tầng (vì fixture chỉ thêm claim hạ tầng mới, không đụng claim đang chấm) nhưng vẫn lệch ở đây (`test_new_relation_catches_what_the_three_given_relations_do_not`). Đối chứng hoán vị chỉ bắt thêm tính phụ thuộc thứ tự của A.

## Kết luận

**Ủng hộ hypothesis.** Thước đo có lỗi lọt qua các quan hệ nhóm đã viết sẵn: lỗi `pass_5` với trial hạ tầng lọt qua cả bản B. Quan hệ metamorphic hữu ích vì không cần đáp án tuyệt đối: ta không biết pass rate "đúng" của một lô, nhưng biết nhân đôi lô hay thêm trial hạ tầng không được đổi tỉ lệ. Lưu ý quan hệ mới dựa trên cách diễn giải của nhóm về pass^5; nếu giảng viên định nghĩa pass^5 coi claim không đủ seed là fail thì kết luận về điểm này đảo lại. Quan hệ còn thiếu: mỗi quan hệ chỉ kiểm một fixture rất nhỏ (workflow, 6 claim), chưa có quan hệ cho nhiều shape cùng lúc hay cho `trial_pass`.

## Giới hạn

Fixture rất nhỏ; mỗi bản chỉ được kiểm trên đó. Không chạy thử `trial_pass` hay grader hidden. MockLLM và cost mô phỏng không liên quan trực tiếp đến thước đo `summarize` nhưng là giới hạn chung của lab.
