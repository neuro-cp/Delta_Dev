from pathlib import Path

from orchestration.runtime.continuity_episodic_learning import (
    AUTHORITY_EFFECT_NONE,
    ContinuityStateBundle,
    DurableOperationalLesson,
    EpisodicRecord,
    LatentConcern,
    LearnedStrategyPreference,
    SaliencePressure,
    apply_continuity_influence,
    evaluate_transfer,
    read_bundle,
    retrieve_continuity,
    validate_bundle,
    write_bundle,
)


def _episode() -> EpisodicRecord:
    return EpisodicRecord(
        episode_id="campaign-a",
        objective="Keep continuity transfer narrow and evidence-linked.",
        outcome_summary="A narrow evidence bridge beat a broader memory framework.",
        evidence_refs=("ev-a-plan-revision", "ev-a-artifact"),
        artifact_refs=("artifact-a",),
        model_operation_refs=("op-a-reflect",),
        restart_refs=("restart-a",),
    )


def _valid_bundle() -> ContinuityStateBundle:
    episode = _episode()
    return ContinuityStateBundle(
        bundle_id="bundle-a",
        gate_id="CONTINUITY_AND_EPISODIC_LEARNING_MARATHON_1",
        episodic_records=(episode,),
        created_from=("campaign-a",),
        continuity_records=(
            DurableOperationalLesson(
                record_id="lesson-evidence-first",
                record_type="durable_operational_lesson",
                summary="Prior campaign progressed only after evidence-linked steps replaced broad architecture scaffolding.",
                source_episode_ids=("campaign-a",),
                evidence_refs=("ev-a-plan-revision",),
                status="supported",
                confidence=0.82,
                context_tags=("continuity transfer", "evidence-linked", "architecture drift"),
                strategy_preference="Prefer a narrow evidence-linked bridge before adding new schema or UI.",
                expected_failure_avoided="architecture drift",
                invalidation_condition="A later live transition requires new runtime architecture.",
            ),
            LearnedStrategyPreference(
                record_id="pref-baseline-transfer",
                record_type="learned_strategy_preference",
                summary="A later related objective should compare continuity-enabled behavior against a baseline.",
                source_episode_ids=("campaign-a",),
                evidence_refs=("ev-a-artifact",),
                status="supported",
                confidence=0.76,
                context_tags=("transfer comparison", "baseline", "episodic learning"),
                preferred_strategy="Run baseline and transfer branches before claiming learning.",
                applicable_scope="continuity transfer gates with related but non-identical objectives",
                counterexample_condition="No prior related campaign exists.",
                invalidation_condition="Baseline cannot be isolated.",
            ),
            LatentConcern(
                record_id="concern-salience-authority",
                record_type="latent_concern",
                summary="Salience must influence attention without creating permission.",
                source_episode_ids=("campaign-a",),
                evidence_refs=("ev-a-plan-revision",),
                status="supported",
                confidence=0.7,
                context_tags=("authority", "salience", "permission"),
                invalidation_condition="Operator grants explicit authority.",
            ),
            SaliencePressure(
                record_id="pressure-reopen-drift",
                record_type="salience_pressure",
                summary="Reopen architecture-drift concern when a plan proposes new UI or schema work.",
                source_episode_ids=("campaign-a",),
                evidence_refs=("ev-a-plan-revision",),
                status="supported",
                confidence=0.68,
                context_tags=("architecture drift", "schema", "UI"),
                pressure_type="latent_concern",
                attention_effect="prioritize checking whether the missing transition really requires new architecture",
                invalidation_condition="The plan contains no UI, schema, or runtime expansion.",
            ),
        ),
    )


def test_valid_bundle_requires_evidence_and_no_authority_effect() -> None:
    bundle = _valid_bundle()

    valid, reasons = validate_bundle(bundle)

    assert valid is True
    assert reasons == ()
    assert {record.authority_effect for record in bundle.continuity_records} == {AUTHORITY_EFFECT_NONE}


def test_invalid_salience_and_concern_are_rejected() -> None:
    episode = _episode()
    bundle = ContinuityStateBundle(
        bundle_id="bad",
        gate_id="CONTINUITY_AND_EPISODIC_LEARNING_MARATHON_1",
        episodic_records=(episode,),
        created_from=("campaign-a",),
        continuity_records=(
            SaliencePressure(
                record_id="bad-pressure",
                record_type="salience_pressure",
                summary="Pressure tries to authorize work.",
                source_episode_ids=("campaign-a",),
                evidence_refs=("ev-a-plan-revision",),
                authority_effect="permission_granted",
                pressure_type="not-real",
            ),
            LatentConcern(
                record_id="bad-concern",
                record_type="latent_concern",
                summary="Concern hardened into truth.",
                source_episode_ids=("campaign-a",),
                evidence_refs=("ev-a-plan-revision",),
                belief_claim="The broad framework is always wrong.",
            ),
        ),
    )

    valid, reasons = validate_bundle(bundle)

    assert valid is False
    assert "authority_effect_not_none:bad-pressure" in reasons
    assert "invalid_pressure_type:bad-pressure" in reasons
    assert "latent_concern_hardened_into_belief:bad-concern" in reasons


def test_bundle_persists_and_retrieves_only_related_continuity(tmp_path: Path) -> None:
    path = tmp_path / "continuity.json"
    write_bundle(path, _valid_bundle())
    bundle = read_bundle(path)

    related = retrieve_continuity(
        bundle,
        objective="Build continuity transfer evidence with a baseline and avoid architecture drift.",
        context_tags=("episodic learning", "baseline", "schema"),
    )
    unrelated = retrieve_continuity(
        bundle,
        objective="Tune rendering colors for a graph view.",
        context_tags=("visual theme", "palette"),
    )

    assert related.selected_record_ids
    assert "pref-baseline-transfer" in related.selected_record_ids
    assert unrelated.selected_record_ids == ()


def test_influence_changes_plan_without_granting_authority() -> None:
    bundle = _valid_bundle()
    packet = retrieve_continuity(
        bundle,
        objective="Continue episodic learning transfer with evidence comparison.",
        context_tags=("continuity transfer", "schema", "evidence"),
    )
    before = (
        "create a new UI panel for continuity state",
        "add a generic framework for future memory",
        "write the comparison evaluator",
    )

    after, event = apply_continuity_influence(
        objective="Continue episodic learning transfer with evidence comparison.",
        before_plan=before,
        packet=packet,
        event_id="influence-b-transfer",
    )

    assert "create a new UI panel for continuity state" not in after
    assert "add a generic framework for future memory" not in after
    assert "write the comparison evaluator" in after
    assert "scope_control" in event.changed_dimensions
    assert event.authority_effect == AUTHORITY_EFFECT_NONE


def test_evaluator_rejects_storage_only_and_accepts_useful_transfer() -> None:
    bundle = _valid_bundle()
    empty_packet = retrieve_continuity(
        bundle,
        objective="Unrelated graph color work.",
        context_tags=("palette",),
    )

    storage_only = evaluate_transfer(
        baseline_metrics={"continuity_enabled": False, "unproductive_cycles": 2},
        transfer_metrics={"continuity_enabled": True, "unproductive_cycles": 2},
        packet=empty_packet,
        influence_events=(),
    )

    packet = retrieve_continuity(
        bundle,
        objective="Run continuity transfer comparison without architecture drift.",
        context_tags=("continuity transfer", "baseline", "architecture drift"),
    )
    after, event = apply_continuity_influence(
        objective="Run continuity transfer comparison without architecture drift.",
        before_plan=("add a generic framework", "write baseline comparison"),
        packet=packet,
        event_id="influence-pass",
    )
    passed = evaluate_transfer(
        baseline_metrics={
            "continuity_enabled": False,
            "time_to_useful_first_action": 3,
            "unproductive_cycles": 2,
            "scope_drift_events": 1,
            "evidence_quality": 2,
            "final_artifact_quality": 3,
        },
        transfer_metrics={
            "continuity_enabled": True,
            "time_to_useful_first_action": 1,
            "unproductive_cycles": 0,
            "scope_drift_events": 0,
            "evidence_quality": 4,
            "final_artifact_quality": 4,
            "avoided_known_failure": True,
        },
        packet=packet,
        influence_events=(event,),
    )

    assert after[0] == "inspect prior evidence links before selecting implementation work"
    assert storage_only["passed"] is False
    assert "no_continuity_retrieved" in storage_only["failure_reasons"]
    assert passed["passed"] is True
    assert "scope_drift_events" in passed["improved_dimensions"]
