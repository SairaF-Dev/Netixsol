"""Tests for the Day 3 regex graph extraction: entity resolution helpers."""
from src.graph.regex_extract import _section_labels, case_key, norm_citation, norm_name


def test_reporter_citations_are_normalised():
    assert norm_citation("PLD 2016 Supreme Court 358") == norm_citation("PLD 2016 SC 358") == "PLD 2016 SC 358"
    assert norm_citation("PLD 2010 Lahore 5") == norm_citation("PLD 2010 Lah. 5")
    assert norm_citation("2019 PCr.LJ 12") == norm_citation("2019 PCr. LJ 12")


def test_case_numbers_map_to_one_key():
    assert case_key("Civil Petition No. 624 of 2023") == case_key("C.P. 624/2023") == "CP-624-2023"
    assert case_key("Criminal Petition No. 645-L of 2025") == "CRLP-645-L-2025"
    assert case_key("Writ Petition No.9563/2010") == "WP-9563-2010"
    assert case_key("no case here") is None


def test_section_labels_and_names():
    assert _section_labels("Section 46 read with 45B ") == ["Section 46", "Section 45B"]
    assert _section_labels("Article 185(3) ") == ["Article 185"]
    assert norm_name("Mr. Justice Syed Mansoor Ali Shah") == norm_name("Justice Mansoor Ali Shah")


def test_judge_titles_are_dropped():
    assert norm_name("Justice Yahya Afridi, CJ") == norm_name("Mr. Justice Yahya Afridi")


def test_provision_references_with_their_law():
    from src.graph.regex_extract import provision_refs

    refs = lambda text: [(labels, act) for labels, act, _ in provision_refs(text)]
    assert refs("lodged under Sections 336, 337-L (i), (ii), 506 & 34 of Pakistan Penal Code, 1860") == [
        (["Section 336", "Section 337L", "Section 506", "Section 34"], "Pakistan Penal Code")]
    assert refs("Benefit of section 382-B, Cr.P.C. was extended.") == [(["Section 382B"], "Cr.P.C.")]
    assert refs("rights under Article 10-A of the Constitution.") == [(["Article 10A"], "Constitution")]
    assert refs("invoking Order XVII Rule 3, C.P.C., closed") == [(["Order XVII Rule 3"], "C.P.C.")]
    assert refs("under Order 39 Rule 1 & 2 of Civil Procedure Code") [0][0] == ["Order XXXIX Rule 1"]
    assert refs("Section 122 of the Transfer of Property Act, 1882") == [(["Section 122"], "Transfer of Property Act")]
    assert refs("section 2 of the Supreme Court (Practice and Procedure) Act, 2023") == [
        (["Section 2"], "Supreme Court (Practice and Procedure) Act")]
    assert refs("(see section 126 of the Contract Act).") == [(["Section 126"], "Contract Act")]
    assert refs("section 540 of the Code emphasizing") == [(["Section 540"], "Code")]     # resolved via "the Code"
    assert refs("Article 26 prohibits discrimination") == [(["Article 26"], None)]       # law from context
    assert refs("learned Judicial Magistrate Section-30, Model Town") == []               # a magistrate's class


def test_act_aliases_and_extra_citation_formats():
    from src.graph.regex_extract import act_alias, citations_in

    assert act_alias("Code of Criminal Procedure, 1898") == act_alias("Criminal Procedure Code") == act_alias("Cr.P.C.")
    assert act_alias("Qanoon-e-Shahadat Order") == act_alias("Qanun-e-Shahadat, 1984") == act_alias("QSO")
    assert act_alias("West Pakistan Family Courts Act, 1964") == act_alias("Family Courts Act")
    assert citations_in("AIR 1975 Pat. 239; (1992) 3 SCC 106; 2025 SCP 405; PLD 1958 SC (Pak.) 41; the 102022 SCMR 1946") == [
        "2022 SCMR 1946", "AIR 1975 Pat. 239", "(1992) 3 SCC 106", "2025 SCP 405", "PLD 1958 SC (Pak.) 41"]


def test_judge_names_are_cleaned_and_variants_merged():
    from src.graph.regex_extract import clean_judge, judge_variants

    assert clean_judge("a H Mr. Justice Syed Hasan Azhar Rizvi :") == "Justice Syed Hasan Azhar Rizvi"
    assert clean_judge("Justice Ishtiaq Ibrahim S 2 / wz") == "Justice Ishtiaq Ibrahim"
    assert clean_judge("i authority in the large interest of justice while") is None
    assert clean_judge("Justice") is None
    merged = judge_variants(["naeem akhtar afghan", "naeem akhter afghan", "munib akhtar"])
    assert merged["naeem akhter afghan"] == "naeem akhtar afghan" and merged["munib akhtar"] == "munib akhtar"
