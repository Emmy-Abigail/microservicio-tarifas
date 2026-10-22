from collections import Counter

from app.data import geography


def test_dataset_totals():
    assert len(geography.list_districts()) == 33
    assert len(geography.list_sedes()) == 5


def test_districts_per_zone():
    # 1 Norte, 2 Centro, 3 Sur, 4 Este, 5 Oeste
    per_zone = Counter(district["id_zona"] for district in geography.list_districts())
    assert per_zone == {1: 6, 2: 8, 3: 8, 4: 6, 5: 5}


def test_one_sede_per_zone():
    assert sorted(sede["id_zona"] for sede in geography.list_sedes()) == [1, 2, 3, 4, 5]


def test_each_sede_is_in_a_district_of_its_zone():
    for sede in geography.list_sedes():
        district = geography.get_district(sede["ubigeo_distrito"])
        assert district is not None
        assert district["id_zona"] == sede["id_zona"]


def test_coordinates_are_inside_lima_and_callao():
    for point in [*geography.list_sedes(), *geography.list_districts()]:
        assert -12.4 < point["lat"] < -11.7
        assert -77.3 < point["lng"] < -76.7


def test_zones_have_codes():
    assert geography.get_zone(1)["codigo"] == "NORTE"
    assert geography.get_zone(5)["codigo"] == "OESTE"


def test_unknown_lookups_return_none():
    assert geography.get_sede(99) is None
    assert geography.get_district("000000") is None
    assert geography.get_zone(99) is None
