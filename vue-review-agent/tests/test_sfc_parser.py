from agents.sfc_parser import parse_vue_sfc,extract_ast_info


def test_parse_splits_sections(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    assert "v-for" in sfc.template
    assert "reactive" in sfc.script
    assert ".card" in sfc.style

def test_parse_detects_script_setup(good_vue_code):
    sfc = parse_vue_sfc(good_vue_code)
    assert sfc.is_script_setup is True

def test_extract_detects_v_html(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code,sfc)
    assert info["has_v_html"] is True

def test_extract_detects_v_for_without_key(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_v_for_without_key"] is True

def test_extract_detects_eval(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_eval"] is True

def test_extract_detects_style_scoped(good_vue_code):
    sfc = parse_vue_sfc(good_vue_code)
    info = extract_ast_info(good_vue_code, sfc)
    assert info["has_style_scoped"] is True

def test_extract_detects_missing_scoped(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_style_scoped"] is False

def test_extract_detects_hardcoded_secret(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_hardcoded_secret"] is True