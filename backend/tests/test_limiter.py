from unittest.mock import MagicMock
from app.limiter import get_real_ip


def _make_request(forwarded_for=None, client_host=None):
    req = MagicMock()
    req.headers.get = lambda key, default=None: (
        forwarded_for if key == "x-forwarded-for" else default
    )
    req.client = MagicMock(host=client_host) if client_host else None
    return req


class TestGetRealIp:
    def test_ip_unico_no_header(self):
        req = _make_request(forwarded_for="1.2.3.4")
        assert get_real_ip(req) == "1.2.3.4"

    def test_multiplos_hops_retorna_ultimo(self):
        # Railway acrescenta o IP real do cliente como último hop;
        # os anteriores podem ser forjados.
        req = _make_request(forwarded_for="fake.ip, proxy.ip, 9.8.7.6")
        assert get_real_ip(req) == "9.8.7.6"

    def test_dois_hops_retorna_segundo(self):
        req = _make_request(forwarded_for="forjado, 203.0.113.5")
        assert get_real_ip(req) == "203.0.113.5"

    def test_sem_header_usa_client_host(self):
        req = _make_request(forwarded_for=None, client_host="10.0.0.1")
        assert get_real_ip(req) == "10.0.0.1"

    def test_sem_header_sem_client_retorna_localhost(self):
        req = MagicMock()
        req.headers.get = lambda key, default=None: default
        req.client = None
        assert get_real_ip(req) == "127.0.0.1"

    def test_espacos_em_volta_dos_hops_sao_removidos(self):
        req = _make_request(forwarded_for="  forjado  ,  192.168.0.1  ")
        assert get_real_ip(req) == "192.168.0.1"

    def test_ip_unico_sem_espacos(self):
        req = _make_request(forwarded_for="5.6.7.8")
        assert get_real_ip(req) == "5.6.7.8"
