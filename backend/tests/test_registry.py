from app.workflows.registry import workflows


def test_finance_has_four_workflows_one_live():
    finance = [w for w in workflows().values() if w.department == "finance"]
    assert [w.number for w in finance] == [1, 2, 3, 4]
    assert [w.status for w in finance] == ["live", "planned", "planned", "planned"]
