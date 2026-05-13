"""
Testes para o serviço de detecção de cópias.

Cobre _jaccard_word_similarity e _calcular_flags com edge cases
de textos idênticos, vazios, e pares abaixo do threshold.
"""
from app.services.detection_service import _jaccard_word_similarity, _calcular_flags


class TestJaccardWordSimilarity:
    def test_textos_identicos(self):
        assert _jaccard_word_similarity("ola mundo", "ola mundo") == 1.0

    def test_textos_sem_palavras_comuns(self):
        assert _jaccard_word_similarity("gato dorme", "carro corre") == 0.0

    def test_overlap_parcial(self):
        sim = _jaccard_word_similarity("a b c", "a b d")
        # interseção={a,b} união={a,b,c,d} → 2/4 = 0.5
        assert abs(sim - 0.5) < 0.01

    def test_string_vazia_a(self):
        assert _jaccard_word_similarity("", "algo aqui") == 0.0

    def test_string_vazia_b(self):
        assert _jaccard_word_similarity("algo aqui", "") == 0.0

    def test_ambas_vazias(self):
        assert _jaccard_word_similarity("", "") == 0.0

    def test_subconjunto_completo(self):
        # "a b" é subconjunto de "a b c" → 2/3
        sim = _jaccard_word_similarity("a b", "a b c")
        assert abs(sim - 2 / 3) < 0.01


class TestCalcularFlags:
    def _entrada(self, questao_id, pares):
        """Monta questao_map a partir de [(resultado_id, resposta_id, texto)]."""
        return {questao_id: pares}

    def test_textos_identicos_sao_flagados(self):
        qmap = self._entrada("q1", [
            ("res1", "resp1", "A velocidade da luz é 300000 km/s"),
            ("res2", "resp2", "A velocidade da luz é 300000 km/s"),
        ])
        flags = _calcular_flags(qmap)
        assert len(flags) == 2
        flagged_ids = {f["id"] for f in flags}
        assert "resp1" in flagged_ids
        assert "resp2" in flagged_ids

    def test_textos_dissimilares_nao_sao_flagados(self):
        qmap = self._entrada("q1", [
            ("res1", "resp1", "A resposta é A"),
            ("res2", "resp2", "Não sei a resposta desta questão"),
        ])
        flags = _calcular_flags(qmap)
        assert flags == []

    def test_um_unico_aluno_nao_compara(self):
        qmap = self._entrada("q1", [
            ("res1", "resp1", "Qualquer coisa"),
        ])
        flags = _calcular_flags(qmap)
        assert flags == []

    def test_questao_sem_respostas_nao_compara(self):
        flags = _calcular_flags({"q1": []})
        assert flags == []

    def test_texto_vazio_ignorado_pelo_detectar_copias(self):
        # _calcular_flags recebe apenas entradas com texto não-vazio
        # (o filtro está em detectar_copias antes da chamada)
        # Aqui garantimos que textos vazios não causam crash
        qmap = self._entrada("q1", [
            ("res1", "resp1", ""),
            ("res2", "resp2", ""),
        ])
        # Jaccard de strings vazias → 0.0 < threshold → sem flags
        flags = _calcular_flags(qmap)
        assert flags == []

    def test_tres_alunos_com_respostas_iguais_flagam_todos(self):
        texto = "A fórmula de Bhaskara resolve equações do segundo grau"
        qmap = self._entrada("q1", [
            ("res1", "resp1", texto),
            ("res2", "resp2", texto),
            ("res3", "resp3", texto),
        ])
        flags = _calcular_flags(qmap)
        flagged_ids = {f["id"] for f in flags}
        # Três pares: (1,2) (1,3) (2,3) → cada id aparece pelo menos uma vez
        assert {"resp1", "resp2", "resp3"} == flagged_ids

    def test_multiplas_questoes_independentes(self):
        texto_copia = "resposta copiada igual em tudo"
        texto_unico = "resposta diferente única"
        qmap = {
            "q1": [
                ("r1", "resp1", texto_copia),
                ("r2", "resp2", texto_copia),
            ],
            "q2": [
                ("r1", "resp3", texto_unico),
                ("r2", "resp4", texto_unico[:5] + " totalmente diferente"),
            ],
        }
        flags = _calcular_flags(qmap)
        flagged_ids = {f["id"] for f in flags}
        # Só q1 deve ter cópias
        assert "resp1" in flagged_ids
        assert "resp2" in flagged_ids
