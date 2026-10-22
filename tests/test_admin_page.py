async def test_admin_page_is_served_without_key(client):
    del client.headers["X-API-Key"]

    response = await client.get("/admin")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "X-API-Key" in response.text
