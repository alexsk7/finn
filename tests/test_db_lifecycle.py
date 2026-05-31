def test_db_lifecycle_exercises_teardown_artifact_cleanup(test_db_lifecycle, db_conn):
    """Exercise DB setup/teardown path; fixture teardown enforces file cleanup."""
    db_conn.execute("INSERT INTO app_flags (key, value) VALUES ('lifecycle_test', '1')")

    assert test_db_lifecycle.exists()
