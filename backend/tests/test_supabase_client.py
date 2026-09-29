from supabase import create_client


def test_modern_supabase_secret_key_format_is_accepted() -> None:
    client = create_client(
        "https://example.supabase.co",
        "sb_secret_test_key",
    )
    assert client.supabase_key == "sb_secret_test_key"
