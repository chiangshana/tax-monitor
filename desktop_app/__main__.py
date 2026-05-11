import os

from desktop_app.app import main


def configure_tls_bundle():
    try:
        import certifi
    except Exception:
        return
    bundle = certifi.where()
    if not bundle or not os.path.exists(bundle):
        return
    os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle)
    os.environ.setdefault("SSL_CERT_FILE", bundle)


if __name__ == "__main__":
    configure_tls_bundle()
    main()
