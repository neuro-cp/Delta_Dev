# Runtime Pathology Duplicate Code

## Duplicate Function Names
```json
{
  "_render": 46,
  "_render_markdown": 43,
  "_stable_id": 85,
  "as_dict": 1321,
  "audit_summary": 349,
  "build_graph_export_metadata": 330,
  "build_objects": 330,
  "demo_payload": 330,
  "diagnostics": 210,
  "graph_export_metadata": 330,
  "json_export": 330,
  "markdown_export": 210,
  "metrics": 210,
  "prohibited_capabilities": 210,
  "report_payload": 349,
  "safety_invariants": 332,
  "summary": 330,
  "validate_module": 330,
  "write_report": 350
}
```

## Duplicate Class Names
```json
{
  "CognitiveBenchmarkSuite": 2,
  "ConfidencePropagationGraphMetadata": 2,
  "ConfidencePropagationObject": 2,
  "ExecutiveAudit": 2,
  "ExecutivePlannerGraphMetadata": 2,
  "ExecutivePlannerObject": 2,
  "ExecutiveSimulation": 2,
  "ExecutiveTimeline": 2,
  "ExternalEvidenceRequest": 2,
  "FeedbackSignalType": 2,
  "Finding": 2,
  "IntegrationPreview": 2,
  "Investigation": 2,
  "InvestigationTransaction": 2,
  "KnowledgeGapAnalysis": 2,
  "ProblemDefinition": 2,
  "ResearchQuestion": 2,
  "Specialist": 2,
  "ToolInvocationPlan": 2
}
```

## Template Module Count
330

## Template Module Sample
- orchestration.runtime.completion_e_kernel_audit_integration
- orchestration.runtime.completion_e_kernel_capability_discovery
- orchestration.runtime.completion_e_kernel_change_detection
- orchestration.runtime.completion_e_kernel_compatibility_layer
- orchestration.runtime.completion_e_kernel_consistency_checks
- orchestration.runtime.completion_e_kernel_dependency_graph
- orchestration.runtime.completion_e_kernel_developer_diagnostics
- orchestration.runtime.completion_e_kernel_diagnostics
- orchestration.runtime.completion_e_kernel_event_hierarchy
- orchestration.runtime.completion_e_kernel_event_prioritization
- orchestration.runtime.completion_e_kernel_execution_traces
- orchestration.runtime.completion_e_kernel_explanation_layer
- orchestration.runtime.completion_e_kernel_failure_simulation
- orchestration.runtime.completion_e_kernel_graph_builder
- orchestration.runtime.completion_e_kernel_graph_diagnostics
- orchestration.runtime.completion_e_kernel_health_metrics
- orchestration.runtime.completion_e_kernel_integrity_validation
- orchestration.runtime.completion_e_kernel_lifecycle
- orchestration.runtime.completion_e_kernel_orchestration_metrics
- orchestration.runtime.completion_e_kernel_pipeline_optimizer
- orchestration.runtime.completion_e_kernel_profiling
- orchestration.runtime.completion_e_kernel_recovery_planning
- orchestration.runtime.completion_e_kernel_replay
- orchestration.runtime.completion_e_kernel_rollback_coordinator
- orchestration.runtime.completion_e_kernel_routing
- orchestration.runtime.completion_e_kernel_runtime_comparison
- orchestration.runtime.completion_e_kernel_runtime_explorer
- orchestration.runtime.completion_e_kernel_runtime_snapshots
- orchestration.runtime.completion_e_kernel_serialization
- orchestration.runtime.completion_e_kernel_state_validation
- orchestration.runtime.completion_e_kernel_statistics
- orchestration.runtime.completion_e_kernel_timing_metadata
- orchestration.runtime.completion_e_kernel_transaction_manager
- orchestration.runtime.completion_e_kernel_validation_reports
- orchestration.runtime.completion_e_kernel_visualization_metadata
- orchestration.runtime.completion_f_concept_hierarchy
- orchestration.runtime.completion_f_concept_inheritance
- orchestration.runtime.completion_f_concept_lineage
- orchestration.runtime.completion_f_confidence_graph
- orchestration.runtime.completion_f_cross_reference_engine
- orchestration.runtime.completion_f_dependency_graph_expansion
- orchestration.runtime.completion_f_entity_clustering
- orchestration.runtime.completion_f_evidence_lineage_graph
- orchestration.runtime.completion_f_evidence_neighborhoods
- orchestration.runtime.completion_f_graph_compression
- orchestration.runtime.completion_f_graph_diagnostics
- orchestration.runtime.completion_f_graph_integrity_validation
- orchestration.runtime.completion_f_graph_partitioning
- orchestration.runtime.completion_f_graph_statistics
- orchestration.runtime.completion_f_graph_traversal_strategies

## Dominant Class Suffixes
```json
{
  "": 3,
  "CognitiveBenchmarkSuite": 2,
  "ConfidencePropagationGraphMetadata": 2,
  "ConfidencePropagationObject": 2,
  "EvidenceCollectionPlan": 1,
  "ExecutiveAudit": 2,
  "ExecutivePlannerGraphMetadata": 2,
  "ExecutivePlannerObject": 2,
  "ExecutiveSimulation": 2,
  "ExecutiveTimeline": 2,
  "ExternalEvidenceRequest": 2,
  "FeedbackSignalType": 2,
  "Finding": 2,
  "GraphMetadata": 210,
  "IntegrationPreview": 2,
  "Investigation": 2,
  "InvestigationPlan": 1,
  "InvestigationTransaction": 2,
  "KnowledgeGapAnalysis": 2,
  "Object": 210,
  "ProblemDefinition": 2,
  "Report": 2,
  "ResearchQuestion": 2,
  "Specialist": 2,
  "ToolInvocationPlan": 2
}
```

## Diagnosis
Large scaffold families intentionally duplicate lifecycle, report, validation, and graph patterns; this is reviewable but should consolidate before activation.
