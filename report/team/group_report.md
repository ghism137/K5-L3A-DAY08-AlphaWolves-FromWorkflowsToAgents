# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: AlphaWolves (một thành viên: Trần Thái Hưng, 2A202603557)
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`): d1787f1

## 2. Mục tiêu và cách tiếp cận

Bài toán: xử lý claim hoàn phí vận chuyển của LogiX-VN bằng bốn kiến trúc (workflow, single, orchestrator, swarm) rồi chọn kiến trúc ít tự chủ nhất mà vẫn làm được việc, dựa trên số đo. Ranh giới chung của cả bốn: số tiền, approval, trần theo đơn và chống ghi trùng do code (`compute_compensation`, `durability.issue_refund`) quyết; model (MockLLM) chỉ soạn chữ hoặc chọn tool đọc.

Nhóm một người nên làm tuần tự: dựng môi trường (Python 3.12, vì máy mặc định là 3.14 nằm ngoài phạm vi 3.11–3.13 mà lab hỗ trợ), viết workflow (đơn giản nhất, làm chuẩn để so), rồi single, rồi orchestrator. Mỗi shape được chạy qua ma trận student T01–T14 trước khi sang shape sau, rồi chạy crash suite và benchmark.

## 3. Giải pháp

Cả ba shape có chung bộ khung: đọc claim bằng `get_claim_view`, thiếu `order_id` thì `needs_info`, order không thuộc principal thì `escalated`, quote từ order row (số ngày ghi trong ticket bị bỏ qua), quote bằng 0 thì `denied` mà không gọi host, còn lại gọi `issue_refund` với **quote đầy đủ** và `crash_at`, không bắt `InjectedCrash`. Host tự trừ phần đã hoàn trước đó nên shape không trừ (T14 sẽ fail nếu trừ hai lần).

| Shape | Cách làm | Số lần gọi model mỗi claim (trung bình) |
| --- | --- | --- |
| A `workflow` | Các bước Python cố định; model chỉ soạn câu trả lời | 1.00 |
| B `single` | `run_react` tối đa 8 bước; `decide()` chọn `lookup_order` rồi `compute_compensation` rồi final; mỗi lượt tính một lần gọi model; sau vòng lặp code của shape mới gọi host | 3.79 |
| C `orchestrator` | Handoff dựng bằng `make_handoff` (allowlist, tool chỉ đọc); `run_readonly_investigators` chạy tool đọc; orchestrator là nơi duy nhất gọi host | 2.93 |

Trace ghi: claim_id và cờ có order_id, order view đã qua allowlist, quote, kết quả host, quyết định cuối, và handoff đã sanitize (orchestrator). Trace không ghi nội dung ticket, claim row hay order row thô. Orchestrator không dùng tóm tắt bằng LLM để lọc thông tin: handoff chỉ gồm các field cho phép và không có facts nào từ claim.

## 4. Kết quả

Bộ public: 14 claim × 5 seed (11, 22, 33, 44, 55) = 70 trial mỗi shape, từ `src/reports/benchmark.json`.

| Shape | Pass rate | pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Mean / p95 steps |
| --- | --- | --- | --- | --- | --- | --- |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0 | 28.79 | 4.43 / 5 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0 | 30.04 | 4.43 / 5 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0 | 39.10 | 3.50 / 4 |
| swarm (tham chiếu) | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 / 3 |

Crash safety: 20/20 (`src/reports/crash.json`). Kiểm thử: cổng host `python -m pytest -q` xanh, ma trận student `python -m pytest -q -m student -o addopts=` xanh (248 passed), `src/tests/test_my_shapes.py` thêm test cho ticket-là-dữ-liệu, thoát sớm không ghi ledger, trace không lộ secret, handoff allowlist và giới hạn 8 bước.

Quyết định kiến trúc: chọn `workflow` (xem `report/team/decision_adr.md`). Phiếu nghiên cứu R4 và ablation bỏ seed 55: xem `report/team/research_card.md`; ablation cho thấy swarm chỉ thấp hơn vì một trial `R-swarm-C-002-s55`.

## 5. Khó khăn và cách xử lý

- Python mặc định của máy là 3.14, ngoài phạm vi hỗ trợ (3.11–3.13). Xử lý: tạo venv bằng `py -3.12 -m venv .venv` trong `src/`; `python -m lab8.smoke` in `lab8.smoke pass`.
- Test đầu tiên viết sai giả định "ledger rỗng sau `needs_info`": world state public đã có sẵn 2 dòng refund lịch sử (cho T13, T14). Xử lý: đổi test thành so số dòng trước và sau, và kiểm riêng dòng của claim đó.
- `pytest -k single` khớp cả tên test `test_public_single_run_cases` nên chạy 242 test thay vì 62. Tất cả đều pass; số liệu 62 test mỗi shape lấy từ `-k workflow` và `-k orchestrator`.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/2A202603557_TranThaiHung.md`. Nhóm một người nên mọi phần do một người làm.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`; cost là mô phỏng, không phải hóa đơn API. Bộ public chỉ có 14 claim nên pass 1.000 chưa chứng minh được kết quả trên bộ hidden (40 claim). Quyết định chọn workflow sẽ đổi nếu bộ hidden có claim cần model đọc hiểu ticket mơ hồ, hoặc nếu dùng model thật làm chênh lệch pass rate lớn hơn chênh lệch cost. Chưa tự kiểm trên `student_drop/` vì chưa có thư mục này. Bonus: làm B4 (`report/team/bonus_report.md`) và B7 (`report/team/bonus_report_b7.md`); theo luật chỉ một topic được chấm.

## 8. Tài liệu tham khảo

- Tài liệu và code của lab: `README.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/metrics.md`, `src/lab8/shapes/swarm_reference.py`.
- Nguồn research card (EMNLP 2026, *Rethinking Evaluation of MAS Efficiency*) lấy theo danh sách của lab; chưa đọc bản gốc.
