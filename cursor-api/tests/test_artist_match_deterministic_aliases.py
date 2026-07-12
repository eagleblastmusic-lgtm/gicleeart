from __future__ import annotations


def test_single_token_artist_does_not_use_fuzzy_wikidata_query(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import artist_match as module

    calls: list[str] = []

    def fake_labels_for_query(query: str, *, fetch: bool = True) -> list[str]:
        calls.append(query)
        return ["Nicola Moneta"]

    monkeypatch.setattr(module.wikidata_artists, "labels_for_query", fake_labels_for_query)

    assert module.artist_match("Monet", "Claude Monet", fetch_wikidata=True)
    assert not module.artist_match("Monet", "Nicola Moneta", fetch_wikidata=True)
    assert not module.artist_match("Monet", "Jean-Baptiste Simonet", fetch_wikidata=True)
    assert calls == []


def test_multi_token_artist_can_still_use_wikidata_aliases(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import artist_match as module

    calls: list[str] = []

    def fake_labels_for_query(query: str, *, fetch: bool = True) -> list[str]:
        calls.append(query)
        return ["Domenikos Theotokopoulos"]

    monkeypatch.setattr(module.wikidata_artists, "labels_for_query", fake_labels_for_query)

    assert module.artist_match("El Greco", "Domenikos Theotokopoulos", fetch_wikidata=True)
    assert calls == ["El Greco"]


def test_explicit_qid_aliases_remain_available_for_single_token_name(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import artist_match as module

    calls: list[tuple[str, bool]] = []

    def fake_labels_for_qid(qid: str, *, fetch: bool = True) -> list[str]:
        calls.append((qid, fetch))
        return ["Oscar-Claude Monet"]

    monkeypatch.setattr(module.wikidata_artists, "labels_for_qid", fake_labels_for_qid)

    variants = module.name_variants("Monet", wikidata_qid="Q296", fetch_wikidata=True)
    assert "Oscar-Claude Monet" in variants
    assert calls == [("Q296", True)]
