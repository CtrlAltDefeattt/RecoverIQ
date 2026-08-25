import hashlib
import hmac

from backend.app.adapters.razorpay import RazorpayAdapter


def adapter():
    return RazorpayAdapter(
        key_id="rzp_test_example",
        key_secret="test-key-secret",
        webhook_secret="webhook-secret",
    )


def test_valid_webhook_signature_is_accepted():
    raw_body = b'{"event":"payment.failed"}'
    signature = hmac.new(
        b"webhook-secret",
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    assert adapter().verify_webhook_signature(raw_body, signature) is True


def test_modified_webhook_body_is_rejected():
    original_body = b'{"event":"payment.failed"}'
    signature = hmac.new(
        b"webhook-secret",
        original_body,
        hashlib.sha256,
    ).hexdigest()

    assert (
        adapter().verify_webhook_signature(
            b'{"event":"payment.captured"}',
            signature,
        )
        is False
    )
