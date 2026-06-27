"""Unit tests for the hinge.error exception hierarchy."""

import pytest

from hinge.error import (
    HingeAuthError,
    HingeEmail2FAError,
    HingeError,
    HingeSessionExpiredError,
)


def test_hinge_error_is_exception_subclass():
    assert issubclass(HingeError, Exception)


def test_hinge_error_instantiation_and_message():
    err = HingeError("boom")
    assert isinstance(err, Exception)
    assert str(err) == "boom"


def test_hinge_error_no_message():
    err = HingeError()
    assert str(err) == ""


def test_hinge_error_can_be_raised_and_caught():
    with pytest.raises(HingeError) as excinfo:
        raise HingeError("raised")
    assert str(excinfo.value) == "raised"


def test_auth_error_inheritance():
    assert issubclass(HingeAuthError, HingeError)
    assert issubclass(HingeAuthError, Exception)


def test_auth_error_default_message():
    err = HingeAuthError()
    assert isinstance(err, HingeError)
    assert str(err) == "Authentication failed. Please check your credentials."


def test_auth_error_custom_message():
    err = HingeAuthError("nope")
    assert str(err) == "nope"


def test_auth_error_caught_as_base():
    with pytest.raises(HingeError):
        raise HingeAuthError()


def test_session_expired_inheritance():
    assert issubclass(HingeSessionExpiredError, HingeError)
    assert issubclass(HingeSessionExpiredError, Exception)


def test_session_expired_default_message():
    err = HingeSessionExpiredError()
    assert isinstance(err, HingeError)
    assert str(err) == "Hinge session expired. Re-authenticate."


def test_session_expired_custom_message():
    err = HingeSessionExpiredError("token gone")
    assert str(err) == "token gone"


def test_session_expired_caught_as_base():
    with pytest.raises(HingeError):
        raise HingeSessionExpiredError()


def test_email_2fa_inheritance():
    assert issubclass(HingeEmail2FAError, HingeError)
    assert issubclass(HingeEmail2FAError, Exception)


def test_email_2fa_attributes_and_message():
    err = HingeEmail2FAError("case-123", "person@example.com")
    assert err.case_id == "case-123"
    assert err.email == "person@example.com"
    assert str(err) == "Email 2FA required. Check email (person@example.com)."


def test_email_2fa_message_embeds_email():
    err = HingeEmail2FAError(case_id="abc", email="user@test.dev")
    assert "user@test.dev" in str(err)
    assert err.case_id == "abc"


def test_email_2fa_caught_as_base_and_keeps_attrs():
    with pytest.raises(HingeError) as excinfo:
        raise HingeEmail2FAError("c1", "a@b.co")
    caught = excinfo.value
    assert isinstance(caught, HingeEmail2FAError)
    assert caught.case_id == "c1"
    assert caught.email == "a@b.co"


def test_subclasses_are_distinct():
    assert not issubclass(HingeAuthError, HingeSessionExpiredError)
    assert not issubclass(HingeSessionExpiredError, HingeEmail2FAError)
    assert not issubclass(HingeEmail2FAError, HingeAuthError)
