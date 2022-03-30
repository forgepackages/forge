from forge.email import TemplateEmail


def test_template_email(monkeypatch, settings, mailoutbox):
    monkeypatch.setattr(
        TemplateEmail,
        "render_html",
        lambda self: "<p>Hi!</p>",
    )
    settings.DEFAULT_FROM_EMAIL = "from@example.com"
    settings.DEFAULT_FROM_NAME = "App"
    settings.DEFAULT_REPLYTO_EMAIL = "support@example.com"

    email = TemplateEmail(
        to="test@example.com",
        subject="Test email",
        template="test",
    )

    assert email.django_email.to == ["test@example.com"]
    assert email.django_email.from_email == "App <from@example.com>"
    assert email.django_email.reply_to == ["support@example.com"]
    assert email.django_email.body == "Hi!"
    assert email.django_email.alternatives == [("<p>Hi!</p>", "text/html")]

    assert len(mailoutbox) == 0
    email.send()
    assert len(mailoutbox) == 1
