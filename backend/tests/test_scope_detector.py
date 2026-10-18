from app.models.response import ScopeStatus


def test_personal_advice_is_out_of_scope():
    from app.safety.scope_detector import detect_scope
    status, msg = detect_scope("I have diabetes, what should I do?")
    assert status == ScopeStatus.OUT_OF_SCOPE
    assert len(msg) > 0


def test_unsafe_dosage_question():
    from app.safety.scope_detector import detect_scope
    status, msg = detect_scope("How much insulin should I inject?")
    assert status == ScopeStatus.UNSAFE


def test_guideline_question_is_supported():
    from app.safety.scope_detector import detect_scope
    status, _ = detect_scope("What does ADA recommend for HbA1c targets?")
    assert status == ScopeStatus.SUPPORTED


def test_ambiguous_question_defaults_to_supported():
    from app.safety.scope_detector import detect_scope
    status, _ = detect_scope("What are the glycemic targets?")
    assert status == ScopeStatus.SUPPORTED


def test_who_question_is_supported():
    from app.safety.scope_detector import detect_scope
    status, _ = detect_scope("What does WHO recommend for hypertension treatment?")
    assert status == ScopeStatus.SUPPORTED


def test_prescribe_me_is_unsafe():
    from app.safety.scope_detector import detect_scope
    status, _ = detect_scope("Can you prescribe me metformin?")
    assert status == ScopeStatus.UNSAFE


def test_my_symptoms_is_out_of_scope():
    from app.safety.scope_detector import detect_scope
    status, _ = detect_scope("My symptoms include fatigue and high blood sugar.")
    assert status == ScopeStatus.OUT_OF_SCOPE