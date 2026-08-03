"""Regression tests for iterative context-summary continuity."""

from unittest.mock import MagicMock, patch

from agent.context_compressor import (
    COMPRESSED_SUMMARY_METADATA_KEY,
    ContextCompressor,
    SUMMARY_PREFIX,
    _MERGED_PRIOR_CONTEXT_HEADER,
    _MERGED_SUMMARY_DELIMITER,
    _RESTART_HANDOFF_PROBE_EXTRA_MESSAGES,
    _SUMMARY_END_MARKER,
)


def _compressor(protect_first_n: int = 1) -> ContextCompressor:
    with patch("agent.context_compressor.get_model_context_length", return_value=100000):
        return ContextCompressor(
            model="test/model",
            threshold_percent=0.85,
            protect_first_n=protect_first_n,
            protect_last_n=1,
            quiet_mode=True,
        )


def _response(content: str):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


def _messages_with_handoff(summary_body: str):
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": f"{SUMMARY_PREFIX}\n{summary_body}"},
        {"role": "assistant", "content": "handoff acknowledged after resume"},
        {"role": "user", "content": "new user turn after resume"},
        {"role": "assistant", "content": "new assistant work after resume"},
        {"role": "user", "content": "more new work after resume"},
        {"role": "assistant", "content": "latest tail response"},
        {"role": "user", "content": "final active request stays in protected tail"},
    ]


def _messages_with_merged_handoff(summary_body: str, prior_tail: str):
    merged = {
        "role": "user",
        "content": (
            f"{_MERGED_PRIOR_CONTEXT_HEADER}\n{prior_tail}\n\n"
            f"{_MERGED_SUMMARY_DELIMITER}\n\n"
            f"{SUMMARY_PREFIX}\n{summary_body}\n\n{_SUMMARY_END_MARKER}"
        ),
        COMPRESSED_SUMMARY_METADATA_KEY: True,
    }
    messages = _messages_with_handoff(summary_body)
    messages[1] = merged
    return messages


def _messages_with_default_handoff(summary_body: str):
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "original task before first compaction"},
        {"role": "assistant", "content": "original answer before first compaction"},
        {"role": "user", "content": "original follow-up before first compaction"},
        {"role": "assistant", "content": f"{SUMMARY_PREFIX}\n{summary_body}"},
        {"role": "user", "content": "new user turn after restart"},
        {"role": "assistant", "content": "new assistant work after restart"},
        {"role": "user", "content": "more new work after restart"},
        {"role": "assistant", "content": "latest tail response"},
        {"role": "user", "content": "final active request stays in protected tail"},
    ]


def _messages_with_summary_at_index(summary_index: int):
    msgs = [{"role": "system", "content": "system prompt"}]
    for idx in range(1, summary_index):
        role = "user" if idx % 2 else "assistant"
        msgs.append({"role": role, "content": f"probe filler {idx}"})
    role = "user" if summary_index % 2 else "assistant"
    msgs.append({"role": role, "content": f"{SUMMARY_PREFIX}\nboundary summary"})
    msgs.extend([
        {"role": "assistant", "content": "new answer"},
        {"role": "user", "content": "tail request"},
    ])
    return msgs








def test_handoff_in_protected_head_is_replaced_not_duplicated():
    """Re-compaction must replace a protected old handoff with the updated one."""
    compressor = _compressor()
    old_summary = "OLD-PROTECTED-HANDOFF unique old summary body"

    with patch("agent.context_compressor.call_llm", return_value=_response("UPDATED summary body")):
        compressed = compressor.compress(_messages_with_handoff(old_summary))

    # The summary may be emitted standalone or merged into the first tail
    # message (alternation corner case), so detect it the same way the
    # compressor does rather than via a startswith(SUMMARY_PREFIX) check.
    summary_messages = [
        msg
        for msg in compressed
        if isinstance(msg, dict)
        and ContextCompressor._is_context_summary_content(msg.get("content"))
    ]
    assert len(summary_messages) == 1
    assert "UPDATED summary body" in str(summary_messages[0]["content"])
    assert old_summary not in str(summary_messages[0]["content"])
    assert old_summary not in "\n".join(str(msg.get("content") or "") for msg in compressed)






def test_recompression_of_current_merged_handoff_preserves_prior_tail_once():
    """Current merged handoffs lose only stale summary data on recompression.

    Composed contract after #57835 (restart head-protection decay): the
    merged handoff's genuine prior-tail content must be RECOVERED — either
    verbatim in the output (pre-decay head protection) or by entering the
    summarizer input so the fresh summary folds it in (post-decay). It must
    never be silently deleted, and the stale summary body must never be
    re-emitted verbatim.
    """
    compressor = _compressor()
    old_summary = "CURRENT-MERGED-OLD-SUMMARY unique continuity facts"
    prior_tail = "PRESERVED-PRIOR-TAIL real user content"

    seen_turns = []

    def _capture(turns, **kwargs):
        seen_turns.extend(turns)
        return ContextCompressor._with_summary_prefix(
            "fresh replacement summary"
        )

    with patch.object(
        compressor,
        "_generate_summary",
        side_effect=_capture,
    ):
        result = compressor.compress(
            _messages_with_merged_handoff(old_summary, prior_tail)
        )

    joined = "\n".join(str(message.get("content", "")) for message in result)
    summarizer_input = "\n".join(str(t.get("content", "")) for t in seen_turns)
    # Prior tail recovered: verbatim in output OR folded via summarizer input.
    assert prior_tail in joined or prior_tail in summarizer_input
    # Never duplicated in the output.
    assert joined.count(prior_tail) <= 1
    assert old_summary not in joined
    assert joined.count(SUMMARY_PREFIX) == 1
    assert "fresh replacement summary" in joined








def test_resume_handoff_after_default_protected_head_decays_initial_turns():
    """Default protect_first_n=3 should not fossilize old protected head turns."""
    compressor = _compressor(protect_first_n=3)
    old_summary = "DEFAULT-RESTART-SUMMARY durable facts from before restart"

    with patch("agent.context_compressor.call_llm", return_value=_response("fresh summary")) as mock_call:
        result = compressor.compress(_messages_with_default_handoff(old_summary))

    prompt = mock_call.call_args.kwargs["messages"][0]["content"]
    assert "PREVIOUS CHECKPOINT — OLDER SUMMARY SOURCE:" in prompt
    assert prompt.count(old_summary) == 1
    assert "original task before first compaction" in prompt
    assert "original answer before first compaction" in prompt
    assert "original follow-up before first compaction" in prompt
    assert f"[ASSISTANT]: {SUMMARY_PREFIX}" not in prompt
    # Grounding (761a0b124e) may prepend a deterministic task-snapshot
    # section — pin the contract, not the exact stored string.
    stored_summary = compressor._previous_summary or ""
    assert stored_summary.endswith("fresh summary")
    assert old_summary not in stored_summary
    assert all(
        "original task before first compaction" not in str(msg.get("content", ""))
        for msg in result
    )
    assert all(
        "original answer before first compaction" not in str(msg.get("content", ""))
        for msg in result
    )
    assert all(
        old_summary not in str(msg.get("content", ""))
        for msg in result
    )


def test_restart_simulation_fresh_compressor_does_not_reprotect_head():
    """Gateway-restart simulation: a FRESH ContextCompressor (in-memory decay
    state reset — compression_count == 0, _previous_summary is None) over a
    transcript that contains a persisted handoff summary must NOT re-protect
    the head. compress_start must reflect decayed protection exactly as a
    live (non-restarted) process would compute it (#57814)."""
    # Live process: has already compacted once, decay is in-memory.
    live = _compressor(protect_first_n=3)
    live.compression_count = 1

    # Restarted process: brand-new compressor, all in-memory state fresh.
    restarted = _compressor(protect_first_n=3)
    assert restarted.compression_count == 0
    assert not restarted._previous_summary

    msgs = _messages_with_default_handoff(
        "PERSISTED-HANDOFF durable facts from before restart"
    )

    # The protected-head boundary the compressor uses for compress_start
    # must be identical for both: system prompt only (decayed protection).
    assert restarted._effective_protect_first_n(msgs) == 0
    assert restarted._protect_head_size(msgs) == live._protect_head_size(msgs) == 1
    restarted_start = restarted._align_boundary_forward(
        msgs, restarted._protect_head_size(msgs)
    )
    assert restarted_start == 1

    # End-to-end: the first post-restart compaction must not preserve the
    # pre-restart head turns or the old handoff verbatim.
    with patch("agent.context_compressor.call_llm", return_value=_response("fresh summary")):
        result = restarted.compress(msgs)
    result_text = "\n".join(str(msg.get("content", "")) for msg in result)
    assert "PERSISTED-HANDOFF durable facts" not in result_text
    assert "original task before first compaction" not in result_text
    assert "original answer before first compaction" not in result_text








def test_zero_protect_first_n_still_folds_restart_fossil():
    """protect_first_n=0 should still self-heal restarted summaries."""
    compressor = _compressor(protect_first_n=0)
    old_summary = "OLD-SUMMARY-ZERO-PROTECT durable facts"
    msgs = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "task one"},
        {"role": "assistant", "content": "answer one"},
        {"role": "user", "content": "task two"},
        {"role": "assistant", "content": f"{SUMMARY_PREFIX}\n{old_summary}"},
        {"role": "user", "content": "active request"},
    ]

    with patch("agent.context_compressor.call_llm", return_value=_response("fresh summary")):
        result = compressor.compress(msgs)

    result_text = "\n".join(str(msg.get("content", "")) for msg in result)
    assert old_summary not in result_text
    assert result_text.index(_SUMMARY_END_MARKER) < result_text.index("active request")
    assert sum(
        1 for msg in result if ContextCompressor._is_context_summary_message(msg)
    ) == 1




def test_restart_fossil_survives_summary_abort_then_retry():
    """An aborted first compaction must not strand the rehydrated fossil.

    Regression for the abort/retry path. The first-compaction self-heal scan
    (``compression_count < 1``) populates ``_previous_summary`` from a fossil
    that drifted past the decay probe. If summary generation then aborts
    (auth / network / ``abort_on_summary_failure``) and returns the transcript
    unchanged, the aborted attempt must not leave that rehydrated state behind:
    otherwise the retry — still ``compression_count == 0`` but now with a
    truthy ``_previous_summary`` — takes the narrow rescan, misses the
    beyond-window fossil, and then discards the rehydrated summary as
    cross-session leakage, copying the fossil forward as a stacked summary.
    """
    compressor = _compressor(protect_first_n=1)
    compressor.abort_on_summary_failure = True
    old_summary = "ABORT-RETRY-OLD-SUMMARY durable facts"
    msgs = [{"role": "system", "content": "system prompt"}]
    msgs += [
        {
            "role": "user" if idx % 2 else "assistant",
            "content": f"filler {idx}",
        }
        for idx in range(1, 6)
    ]
    msgs += [
        {"role": "assistant", "content": f"{SUMMARY_PREFIX}\n{old_summary}"},
        {"role": "user", "content": "active request"},
    ]

    # First compaction aborts on a summary-generation failure. The transcript
    # is returned unchanged AND the self-heal state it rehydrated must be
    # rolled back, so a retry behaves like the original first compaction.
    with patch.object(compressor, "_generate_summary", return_value=None):
        aborted = compressor.compress([dict(m) for m in msgs])
    assert compressor._last_compress_aborted is True
    assert all(m["content"] for m in aborted)  # returned unchanged
    assert compressor.compression_count == 0
    assert compressor._previous_summary is None

    # Retry: the fossil beyond the narrow window is still folded, not copied
    # forward as a second stacked summary.
    with patch("agent.context_compressor.call_llm", return_value=_response("fresh summary")):
        result = compressor.compress([dict(m) for m in msgs])

    assert all(old_summary not in str(msg.get("content", "")) for msg in result)
    assert sum(
        1 for msg in result if ContextCompressor._is_context_summary_message(msg)
    ) == 1




def test_forced_leading_merged_summary_strips_live_tail_from_summary_body():
    """Rehydrating a forced-leading merged summary should ignore live tail."""
    merged = (
        f"{SUMMARY_PREFIX}\nSUMMARY_BODY\n\n"
        f"{_SUMMARY_END_MARKER}\n\n"
        "LIVE_TAIL_REQUEST"
    )

    assert ContextCompressor._is_context_summary_content(merged) is True
    assert ContextCompressor._strip_summary_prefix(merged) == "SUMMARY_BODY"










def test_empty_post_handoff_window_noops_without_summary_call():
    """A latest handoff that consumes the window must not trigger an empty summary.

    Regression test from PR #59526 (#59496), fixture adapted to current main:
    the standalone handoff sits alone in the compressible window, strips to
    None via _strip_context_summary_handoff_message, and leaves
    turns_to_summarize empty — the guard must skip _generate_summary
    entirely instead of wasting an aux LLM call on empty input.
    """
    compressor = _compressor()
    old_summary = "WINDOW-END-SUMMARY durable facts already captured"
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": f"{SUMMARY_PREFIX}\n{old_summary}"},
        {"role": "assistant", "content": "recent tail response"},
        {"role": "user", "content": "tail request"},
        {"role": "assistant", "content": "tail answer"},
        {"role": "user", "content": "latest tail request"},
        {"role": "assistant", "content": "latest tail answer"},
    ]

    with (
        patch.object(compressor, "_find_tail_cut_by_tokens", return_value=2),
        patch.object(compressor, "_generate_summary") as mock_generate_summary,
    ):
        result = compressor.compress(messages, current_tokens=90_000)

    mock_generate_summary.assert_not_called()
    assert result == messages
    # The rehydrated summary state is deliberately kept: the handoff is
    # genuinely present in the returned (unchanged) transcript.
    assert compressor._previous_summary == old_summary
    assert compressor.compression_count == 0
    # Mirrors the sibling no-compressible-window guard (#40803): the shape
    # cannot shrink, so it counts as an ineffective strike (routed through
    # the durable write-through helper) to arm the anti-thrash breaker.
    assert compressor._ineffective_compression_count == 1
    assert compressor._last_compression_savings_pct == 0.0
    assert compressor._last_summary_dropped_count == 0
    assert compressor._last_summary_fallback_used is False
    assert compressor._last_compress_aborted is False
    telemetry = compressor._last_compression_telemetry or {}

    assert telemetry.get("failure_class") == "empty_post_handoff_window"


def _capture_prompt(compressor, turns, **kwargs):
    captured = {}

    def _call(**call_kwargs):
        captured["prompt"] = call_kwargs["messages"][0]["content"]
        return _response("checkpoint body")

    with patch("agent.context_compressor.call_llm", _call):
        compressor._generate_summary(turns, **kwargs)
    return captured["prompt"]


def test_summary_prompt_is_middle_only_with_indexed_head_checkpoint_and_tail():
    compressor = _compressor()
    compressor._summary_head_turn_count = 2
    prompt = _capture_prompt(
        compressor,
        [
            {"role": "user", "content": "MIDDLE-SOURCE-ONE"},
            {"role": "assistant", "content": "MIDDLE-SOURCE-TWO"},
        ],
        preserved_tail_turns=[{"role": "user", "content": "TAIL-SEAM-ONLY"}],
    )

    assert "PRESERVED HEAD — TURNS #1–#2 — KEPT VERBATIM; NOT INCLUDED BELOW" in prompt
    assert "SUMMARY SOURCE — MIDDLE TURNS #3–#4" in prompt
    assert "PRESERVED TAIL — SEAM REFERENCE ONLY; DO NOT SUMMARIZE OR REWRITE — TURNS #5+:" in prompt
    assert "MIDDLE-SOURCE-ONE" in prompt
    assert "MIDDLE-SOURCE-TWO" in prompt
    assert "TAIL-SEAM-ONLY" in prompt
    assert prompt.index("SUMMARY SOURCE") < prompt.index("PRESERVED TAIL")

def test_tail_reference_contains_exact_appended_rows_and_is_not_summary_source():
    compressor = _compressor(protect_first_n=2)
    compressor._find_tail_cut_by_tokens = lambda _messages, _start: 5
    captured = {}

    def _capture(turns, **kwargs):
        captured["middle"] = turns
        captured["tail"] = [row.copy() for row in kwargs["preserved_tail_turns"]]
        return ContextCompressor._with_summary_prefix("fresh checkpoint")

    messages = [
        {"role": "system", "content": "system"},
        {"role": "assistant", "content": "HEAD-VERBATIM"},
        {"role": "assistant", "content": "HEAD-VERBATIM-TWO"},
        {"role": "user", "content": "MIDDLE-ONLY"},
        {"role": "assistant", "content": "MIDDLE-ANSWER"},
        {"role": "user", "content": "TAIL-EXACT-USER"},
        {"role": "assistant", "content": "TAIL-EXACT-ASSISTANT"},
        {"role": "user", "content": "TAIL-EXACT-CURRENT"},
    ]
    with patch.object(compressor, "_generate_summary", side_effect=_capture):
        result = compressor.compress(messages, current_tokens=90_000)

    assert [row["content"] for row in captured["middle"]] == ["MIDDLE-ONLY", "MIDDLE-ANSWER"]
    assert [row["content"] for row in captured["tail"]] == [
        "TAIL-EXACT-USER",
        "TAIL-EXACT-ASSISTANT",
        "TAIL-EXACT-CURRENT",
    ]
    result_text = "\n".join(str(row.get("content", "")) for row in result)
    assert "HEAD-VERBATIM" in result_text
    assert "TAIL-EXACT-USER" in result_text
    assert "TAIL-EXACT-ASSISTANT" in result_text
    assert "TAIL-EXACT-CURRENT" in result_text


def test_tail_reference_preserves_both_sides_of_a_conflict_without_summarizing_tail():
    compressor = _compressor()
    prompt = _capture_prompt(
        compressor,
        [{"role": "user", "content": "CONFLICT-OLD-SIDE"}],
        preserved_tail_turns=[{"role": "user", "content": "CONFLICT-NEW-SIDE"}],
    )
    before_tail = prompt.split("PRESERVED TAIL", 1)[0]
    assert "CONFLICT-OLD-SIDE" in before_tail
    assert "CONFLICT-NEW-SIDE" not in before_tail
    assert "CONFLICT-NEW-SIDE" in prompt
    assert "DO NOT SUMMARIZE OR REWRITE" in prompt


def test_tail_reference_is_bounded_and_redacted_with_the_shared_serializer():
    compressor = _compressor()
    secret = "ghp_" + ("s" * 36)
    tail = [
        {"role": "user", "content": "TAIL-START " + secret + " " + ("x" * 20000) + " TAIL-END-ONE"},
        {"role": "assistant", "content": "TAIL-SECOND " + ("y" * 20000)},
        {"role": "user", "content": "TAIL-THIRD " + ("z" * 20000)},
        {"role": "assistant", "content": "TAIL-END"},
    ]
    serialized = compressor._serialize_for_summary(tail)
    bounded = compressor._bound_summary_input(
        serialized,
        max_chars=16000,
        marker_label="preserved tail reference",
    )
    assert len(bounded) <= 16000
    assert "preserved tail reference truncated" in bounded
    assert secret not in bounded
    prompt = _capture_prompt(compressor, [{"role": "user", "content": "middle"}], preserved_tail_turns=tail)
    assert "TAIL-START" in prompt
    assert secret not in prompt


def test_iterative_prompt_migrates_previous_checkpoint_into_new_middle_and_tail():
    compressor = _compressor()
    compressor._previous_summary = "OLD-CHECKPOINT-FACT"
    prompt = _capture_prompt(
        compressor,
        [{"role": "user", "content": "NEW-MIDDLE-FACT"}],
        preserved_tail_turns=[{"role": "assistant", "content": "NEW-TAIL-FACT"}],
    )
    assert "PREVIOUS CHECKPOINT — OLDER SUMMARY SOURCE:" in prompt
    assert "OLD-CHECKPOINT-FACT" in prompt
    assert "NEW-MIDDLE-FACT" in prompt
    assert "NEW-TAIL-FACT" in prompt


def test_summary_template_marks_hypotheses_unverified():
    prompt = _capture_prompt(
        _compressor(),
        [{"role": "assistant", "content": "The likely cause is a stale cache."}],
    )
    assert "[HYPOTHESIS]" in prompt
    assert "[UNVERIFIED]" in prompt
    assert "Never present an inferred goal as the user's words" in prompt


def test_no_user_summary_template_forces_none_in_user_request_sections():
    compressor = _compressor()
    compressor._summary_has_user_turn = False
    prompt = _capture_prompt(
        compressor,
        [{"role": "assistant", "content": "Internal tool work only."}],
    )
    assert "None. This session contains no user-authored turns." in prompt
    assert "None. No user-authored requests exist." in prompt
    assert "None. No user-authored work is owed to a user." in prompt
    assert 'Do not write "User asked:"' in prompt


def test_reverse_signal_guidance_excludes_superseded_work():
    prompt = _capture_prompt(
        _compressor(),
        [
            {"role": "user", "content": "Implement the old migration plan."},
            {"role": "assistant", "content": "Started the old plan."},
            {"role": "user", "content": "Stop; do not continue that migration."},
        ],
    )
    assert "reverse signal" in prompt
    assert "[CANCELLED]" in prompt
    assert "Exclude completed and cancelled work" in prompt


def test_focus_and_memory_are_guidance_not_evidence():
    prompt = _capture_prompt(
        _compressor(),
        [{"role": "user", "content": "Use the source facts only."}],
        focus_topic="UNSUPPORTED-FOCUS-CLAIM",
        memory_context="MEMORY-SUGGESTED-CLAIM",
    )
    assert "The focus text is guidance, not evidence" in prompt
    assert "Memory-provider context is source material only" in prompt
    assert "MEMORY-SUGGESTED-CLAIM" in prompt


def test_merge_into_tail_preserves_alternation_exception_and_tail_row():
    compressor = _compressor(protect_first_n=2)
    compressor._find_tail_cut_by_tokens = lambda _messages, _start: 5
    captured = {}

    def _capture(turns, **kwargs):
        captured["tail"] = [row.copy() for row in kwargs["preserved_tail_turns"]]
        return ContextCompressor._with_summary_prefix("MERGED-CHECKPOINT")

    messages = [
        {"role": "system", "content": "system"},
        {"role": "assistant", "content": "head assistant"},
        {"role": "assistant", "content": "head assistant two"},
        {"role": "user", "content": "middle user"},
        {"role": "assistant", "content": "middle assistant"},
        {"role": "user", "content": "tail first user"},
        {"role": "assistant", "content": "tail assistant"},
        {"role": "user", "content": "tail latest user"},
    ]
    with patch.object(compressor, "_generate_summary", side_effect=_capture):
        result = compressor.compress(messages, current_tokens=90_000)

    assert captured["tail"][0]["content"] == "tail first user"
    summary_rows = [
        row for row in result
        if ContextCompressor._is_context_summary_content(row.get("content"))
    ]
    assert len(summary_rows) == 1
    assert "MERGED-CHECKPOINT" in summary_rows[0]["content"]
    assert "tail first user" in summary_rows[0]["content"]
