# Báo cáo cá nhân — 2A202603557_TranThaiHung

## 1. Thông tin thành viên

- Họ tên: Trần Thái Hưng
- MSSV: 2A202603557
- Email: sktelfins137@gmail.com
- GitHub: ghism137

## 2. Phần việc phụ trách

Nhóm AlphaWolves chỉ có một thành viên nên phụ trách toàn bộ: ba shape (workflow, single, orchestrator), test, chạy crash suite và benchmark, ADR, research card, báo cáo nhóm, và hai bonus B4 (baseline, ablation, thống kê) và B7 (kiểm toán grader).

## 3. Đóng góp cụ thể

Commit chính:

- `b46afc3` workflow: các bước cố định, quote từ `compute_compensation`, gọi `issue_refund` với quote đầy đủ và `crash_at`.
- `33bbe5e` single: vòng `run_react` tối đa 8 bước, `decide()` chỉ chọn tool đọc, mỗi lượt tính một lần gọi model.
- `6b8d06c` orchestrator: handoff qua `make_handoff`, investigator chỉ có tool đọc, orchestrator là nơi duy nhất gọi host.
- `ac417ba` test: `src/tests/test_my_shapes.py`.
- `1716609`, `ab1772a`: file report do `lab8.benchmark` và `lab8.crash_test` sinh ra, không sửa tay.
- `ea9532f` bonus B7: `src/bonus/grader_relations.py`, quan hệ metamorphic trên ba bản `summarize` và một quan hệ mới về pass^5.
- `65583f7` bonus B4: `src/bonus/variants.py`, `stats.py`, `run_ablation.py`; baseline, ablation, bootstrap CI và McNemar.

Quyết định kỹ thuật: (1) shape luôn truyền quote đầy đủ vào host vì host tự trừ phần đã hoàn theo đơn, tự trừ thì T14 bị trừ hai lần; (2) ticket chỉ là dữ liệu, không dùng số ngày trong ticket để tính tiền; (3) trace không ghi ticket, claim row, order row thô; (4) chọn `workflow` làm shape nộp vì cùng pass 1.000 nhưng ít lần gọi model nhất.

## 4. Bằng chứng

- Test: `python -m pytest -q` (cổng host, gồm test_my_shapes.py), `python -m pytest -q -m student -o addopts=` (248 passed).
- Test do tôi thêm: `test_ticket_delay_is_data_not_order`, `test_missing_order_id_needs_info_and_no_write`, `test_quote_zero_skips_host_so_no_policy_denied_audit`, `test_foreign_order_escalates_without_leaking_order_fields`, `test_trace_never_contains_claim_secrets_or_ticket`, `test_order_already_refunded_is_denied_with_full_quote`, `test_difference_only_is_paid_when_entitlement_grows`, `test_orchestrator_trace_handoff_is_allowlist_only`, `test_single_agent_respects_step_cap_and_counts_model_calls`, `test_workflow_is_cheaper_than_single_and_orchestrator`.
- Test bonus: `src/tests/test_bonus_grader_audit.py` (23 test, `python -m pytest -q tests/test_bonus_grader_audit.py`), `src/tests/test_bonus_ablation.py` (11 test).
- Report: `src/reports/benchmark.json` (workflow, single, orchestrator đều 70/70; swarm fail `R-swarm-C-002-s55`), `src/reports/crash.json` (`20/20`), `src/reports/ablation_no_seed55.json`, `src/reports/bonus_benchmark.json`, `src/reports/bonus_ablation.json`, `src/reports/bonus_grader_audit.json`. Báo cáo bonus: `report/team/bonus_report.md` (B4) và `report/team/bonus_report_b7.md` (B7).

## 5. Công cụ AI đã dùng

Claude Code (Anthropic): đọc đề và code starter, đề xuất plan, viết code ba shape, viết test, soạn nháp tài liệu. Cách kiểm tra kết quả: chạy lại `python -m pytest -q`, `python -m pytest -q -m student -o addopts=`, `python -m lab8.crash_test --count 20 --out reports/crash.json` và `python -m lab8.benchmark ...`; mọi con số trong ADR và báo cáo được lấy từ các file JSON do công cụ sinh ra; chạy `python -m lab8.check_submission`. Không dùng AI để bịa số liệu, run id hay commit.

## 6. Tự đánh giá
t.

**Điều tôi hiểu và giải thích được.**

- *Ranh giới code và model.* Code quyết mọi thứ liên quan đến tiền: số tiền do `compute_compensation` tính từ order row, approval, trần theo đơn và việc ghi ledger do host (`durability.issue_refund`) làm. Model (MockLLM) chỉ soạn câu trả lời (workflow) hoặc chọn tool đọc (single). Nhờ vậy shape sai hay model sai thì host vẫn chặn được.
- *Vì sao truyền quote đầy đủ.* Host tự trừ phần đơn đã được hoàn bởi claim khác. Ở T14 đơn đã hoàn 30.000, nay hỏng hàng có entitlement 150.000: shape truyền 150.000, host ghi phần chênh 120.000. Nếu shape tự trừ trước, host trừ lần nữa và số tiền sai.
- *Trace cố ý không ghi gì.* Không ghi ticket (dữ liệu khách nhập, có thể chứa chuỗi bất kỳ), claim row (có `parent_secret`, `raw_headers`) và order row thô (có SĐT, địa chỉ, tên hàng, ghi chú). Chỉ ghi field đã qua allowlist, vì grader quét trace để tìm secret và PII.
- *Crash và idempotency.* Dòng ledger và audit `refund_committed` nằm trong một transaction; khóa là `refund:{claim_id}`. Shape không bắt `InjectedCrash` để crash xảy ra thật, chạy lại vẫn chỉ một refund (crash suite 20/20).

**Kết quả và mức tin cậy.** Cả ba shape pass 70/70 trên 14 claim public, nên tôi chọn `workflow` vì ít lần gọi model nhất (cost mô phỏng 28.79 so với 30.04, 39.10 và 49.57 của swarm). Tôi biết kết luận này yếu ở ba điểm: chỉ có bộ public 14 claim và chưa có số hidden; khoảng cách cost giữa workflow và single chỉ khoảng 4%; và cost là số mô phỏng của MockLLM, không phải hóa đơn thật. Ở bonus B4, workflow so với swarm chỉ có một cặp lệch (p = 1.0), nên tôi không khẳng định workflow đúng hơn, chỉ rẻ hơn.

**Điều tôi chưa làm hoặc chưa chắc.**

- Chưa đọc bản gốc các paper nêu ở research card và bonus; nguồn ghi theo mô tả của lab.
- Quan hệ metamorphic mới ở B7 (`infra_replace_keeps_pass5`) dựa trên cách tôi diễn giải pass^5
- Phần lớn code được vibecode. Tôi đã đọc lại, chạy lại test, crash suite và benchmark để kiểm tra.

**Nếu làm lại.** Tôi sẽ chạy thử trên `student_drop/` sớm hơn và đọc paper trước khi điền research card, để ablation trả lời câu hỏi của paper thay vì chỉ kiểm tra điểm yếu seed 55 của swarm.
