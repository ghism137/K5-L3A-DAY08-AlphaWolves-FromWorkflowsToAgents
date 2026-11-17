# Báo cáo cá nhân — 2A202603557_TranThaiHung

## 1. Thông tin thành viên

- Họ tên: Trần Thái Hưng
- MSSV: 2A202603557
- Email: sktelfins137@gmail.com
- GitHub: ghism137

## 2. Phần việc phụ trách

Nhóm AlphaWolves chỉ có một thành viên nên phụ trách toàn bộ: ba shape (workflow, single, orchestrator), test, chạy crash suite và benchmark, ADR, research card, báo cáo nhóm.

## 3. Đóng góp cụ thể

Commit chính:

- `b46afc3` workflow: các bước cố định, quote từ `compute_compensation`, gọi `issue_refund` với quote đầy đủ và `crash_at`.
- `33bbe5e` single: vòng `run_react` tối đa 8 bước, `decide()` chỉ chọn tool đọc, mỗi lượt tính một lần gọi model.
- `6b8d06c` orchestrator: handoff qua `make_handoff`, investigator chỉ có tool đọc, orchestrator là nơi duy nhất gọi host.
- `ac417ba` test: `src/tests/test_my_shapes.py`.
- `1716609`, `ab1772a`: file report do `lab8.benchmark` và `lab8.crash_test` sinh ra, không sửa tay.

Quyết định kỹ thuật: (1) shape luôn truyền quote đầy đủ vào host vì host tự trừ phần đã hoàn theo đơn, tự trừ thì T14 bị trừ hai lần; (2) ticket chỉ là dữ liệu, không dùng số ngày trong ticket để tính tiền; (3) trace không ghi ticket, claim row, order row thô; (4) chọn `workflow` làm shape nộp vì cùng pass 1.000 nhưng ít lần gọi model nhất.

## 4. Bằng chứng

- Test: `python -m pytest -q` (cổng host, gồm test_my_shapes.py), `python -m pytest -q -m student -o addopts=` (248 passed).
- Test do tôi thêm: `test_ticket_delay_is_data_not_order`, `test_missing_order_id_needs_info_and_no_write`, `test_quote_zero_skips_host_so_no_policy_denied_audit`, `test_foreign_order_escalates_without_leaking_order_fields`, `test_trace_never_contains_claim_secrets_or_ticket`, `test_order_already_refunded_is_denied_with_full_quote`, `test_difference_only_is_paid_when_entitlement_grows`, `test_orchestrator_trace_handoff_is_allowlist_only`, `test_single_agent_respects_step_cap_and_counts_model_calls`, `test_workflow_is_cheaper_than_single_and_orchestrator`.
- Report: `src/reports/benchmark.json` (workflow, single, orchestrator đều 70/70; swarm fail `R-swarm-C-002-s55`), `src/reports/crash.json` (`20/20`), `src/reports/ablation_no_seed55.json`.

## 5. Công cụ AI đã dùng

Claude Code (Anthropic): đọc đề và code starter, đề xuất plan, viết code ba shape, viết test, soạn nháp tài liệu. Cách kiểm tra kết quả: chạy lại `python -m pytest -q`, `python -m pytest -q -m student -o addopts=`, `python -m lab8.crash_test --count 20 --out reports/crash.json` và `python -m lab8.benchmark ...`; mọi con số trong ADR và báo cáo được lấy từ các file JSON do công cụ sinh ra; chạy `python -m lab8.check_submission`. Không dùng AI để bịa số liệu, run id hay commit.

## 6. Tự đánh giá

(Phần này cần tác giả tự viết sau khi đọc lại bài: mức hiểu của mình về ranh giới code / model, vì sao truyền quote đầy đủ, và trace cố ý không ghi field nào. Người chấm có thể hỏi trực tiếp các phần này.)
