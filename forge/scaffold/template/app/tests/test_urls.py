def test_homepage_exists(client):
    response = client.get("/")
    assert response.status_code in (200, 301, 302)
