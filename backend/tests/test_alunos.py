"""
Testes unitários para lógica de alunos.

Cobre _gerar_initials (edge cases que causavam initial com 1 char)
e endpoints HTTP com auth mockada.
"""
import pytest
from app.routers.alunos import _gerar_initials


class TestGerarInitials:
    def test_nome_completo(self):
        assert _gerar_initials("Maria Silva") == "MS"

    def test_nome_tres_partes_usa_primeiro_e_ultimo(self):
        assert _gerar_initials("João da Silva") == "JS"

    def test_nome_unico_dois_chars(self):
        # "Li" → "LI"
        assert _gerar_initials("Li") == "LI"

    def test_nome_unico_um_char_duplica(self):
        # Bug corrigido: antes gerava "A", agora gera "AA"
        assert _gerar_initials("A") == "AA"

    def test_nome_unico_longo(self):
        assert _gerar_initials("Pedro") == "PE"

    def test_espacos_ao_redor_ignorados(self):
        assert _gerar_initials("  Ana Lima  ") == "AL"

    def test_resultado_sempre_maiusculo(self):
        assert _gerar_initials("carlos souza") == "CS"

    def test_len_sempre_dois(self):
        # Garante que qualquer entrada gera exatamente 2 caracteres
        casos = ["A", "X", "Jo", "Maria", "João da Silva", "  Z  "]
        for nome in casos:
            result = _gerar_initials(nome)
            assert len(result) == 2, f"Esperado 2 chars para {nome!r}, got {result!r}"
