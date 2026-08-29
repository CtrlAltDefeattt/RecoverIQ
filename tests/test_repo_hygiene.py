from scripts.check_repo_hygiene import check_repository


def test_repository_hygiene():
    assert check_repository() == []
