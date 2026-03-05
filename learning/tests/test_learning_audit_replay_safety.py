from learning.audit.learning_audit import LearningAudit


def test_learning_audit_empty_passes():
    audit = LearningAudit()
    audit.audit(proposals=[])
