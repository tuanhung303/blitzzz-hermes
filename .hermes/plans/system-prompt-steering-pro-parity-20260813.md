# Plan: Verify + tune reasoning & tool_loop guardrails cho cron + subagent

Ngày: 2026-08-13. Trạng thái: chưa thực thi. Chủ sở hữu: blitzzz.

## 1. Mục tiêu

Đảm bảo cron job và subagent (delegate_task) kế thừa đúng:
- reasoning effort max (config `agent.reasoning_effort: max` + `reasoning_overrides`
  max cho toàn bộ deepseek/gpt models).
- tool_loop_guardrails (warn/halt khi lặp lỗi) hoạt động, không bị tắt vì chạy
  trong context cron/subagent.

Phạm vi: KHÔNG thêm prompt kỷ luật cho model (đã bỏ theo yêu cầu). Chỉ verify
runtime path + tune config nếu có lỗ hổng.

## 2. Bối cảnh (đã xác nhận bằng đọc code)

- Runtime: `~/.hermes/hermes-agent` (upstream), fork surface: `blitzzz-hermes`.
- Cron agent: `cron/scheduler.py` build AIAgent với `load_soul_identity=True`,
  `skip_memory=True`, `skip_context_files=not _job_workdir`. Model mặc định từ
  `config.model.default` = deepseek-v4-flash, job có thể pin model riêng.
- Subagent: `tools/delegate_tool.py::_build_child_agent` build child AIAgent,
  kế thừa model parent (trừ khi config `delegation.model` pin), `skip_context_files=True`,
  `skip_memory=True`, KHÔNG load SOUL.md (đã chấp nhận - không sửa).
- reasoning_effort resolve qua AIAgent -> `agent_init` (chung 1 path cho chat/cron/subagent).
- tool_loop_guardrails: `agent/tool_guardrails.py`, config `tool_loop_guardrails`
  (warnings_enabled=true, hard_stop_enabled=true; warn: exact=2, same_tool=3,
  no_progress=2). Gắn ở tool executor, áp cho mọi agent có tools.

## 3. Các bước verify (read-only trước, test thực sau)

1. **Reasoning resolve path**: đọc `agent/agent_init.py` (hoặc `agent/model_metadata.py`)
   xác nhận `reasoning_effort` + `reasoning_overrides` được apply cho MỌI AIAgent
   (chat, cron, subagent), không có nhánh bỏ qua khi `skip_memory`/`skip_context_files`.
2. **Cron model mặc định**: đọc `cron/scheduler.py` đoạn build agent, xác nhận
   job không pin model thì dùng `model.default` (flash) và flash có trong
   `reasoning_overrides` -> max. Kiểm tra job pin model khác (vd gpt-5.6-luna)
   vẫn resolve đúng override (luna: max).
3. **Subagent model kế thừa**: đọc `delegate_tool.py` xác nhận child dùng parent
   model + cùng reasoning resolve. Kiểm tra `delegation.model` pin (nếu có trong
   config) không phá override.
4. **tool_loop_guardrails scope**: đọc `agent/tool_guardrails.py` + `agent/tool_executor.py`
   xác nhận guardrails gắn ở executor chung (không gated theo cron/subagent).
   Xác nhận `hard_stop_enabled` mặc định trong code là False nhưng config user bật
   true, và config được load cho cron/subagent (không dùng DEFAULT_CONFIG bỏ qua).
5. **Test thực (sau khi đọc code, chưa sửa gì)**:
   - Chạy 1 cron job đơn giản (ví dụ cronjob action=run job in-house hoặc tạo job
     test) -> xem log telemetry reasoning effort có phải max không.
   - Chạy 1 delegate_task -> xem child log reasoning effort.
   - (nếu cần) trigger 1 tool lặp lỗi 3 lần -> xem guardrail warn có bắn không.

## 4. Tune (chỉ khi verify phát hiện lỗ hổng)

- Nếu cron/subagent không thừa hưởng reasoning_overrides -> fix ở agent_init
  (resolve chung) hoặc thêm override cho path đó. Patch qua fork workflow.
- Nếu hard_stop không active cho cron/subagent -> sửa config load path.
- Nếu guardrails không gắn cho subagent (child dùng executor riêng) -> đảm bảo
  child cũng chạy guardrails.

## 5. Deliverable

- Báo cáo verify (reasoning + guardrails cho cron + subagent): từng bước PASS/FAIL
  kèm bằng chứng (code path + log thực).
- Config/patch diff nếu có lỗ hổng cần sửa, theo đúng fork workflow (patch riêng,
  apply-fork-to-managed.sh, run_tests.sh).
- Không thêm prompt kỷ luật, không đụng SOUL.md.
