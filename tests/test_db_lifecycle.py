from app.db import get_conn


def test_db_lifecycle_exercises_teardown_artifact_cleanup(test_db_lifecycle):
    """Exercise DB setup/teardown path; fixture teardown enforces file cleanup."""
    with get_conn(db_path=str(test_db_lifecycle)) as conn:
        conn.execute("INSERT INTO app_flags (key, value) VALUES ('lifecycle_test', '1')")

    assert test_db_lifecycle.exists()
