from agent.search_engine import expand_with_wordforms


def test_expand_keeps_original():
    result = expand_with_wordforms(["заводы"])
    assert "заводы" in result


def test_expand_adds_lemma():
    result = expand_with_wordforms(["заводы"])
    # лемма для "заводы" - "завод"
    assert any("завод" == w for w in result)


def test_expand_empty_input():
    assert expand_with_wordforms([]) == []


def test_expand_no_duplicate_synonyms():
    # проверяем, что не добавляются синонимы вроде "предприятие" - только словоформы
    result = expand_with_wordforms(["завод"])
    assert "предприятие" not in result
