-- Migration 007: Gabarito PDF upload
-- Adiciona suporte para o professor enviar o gabarito oficial em PDF/imagem.
-- O agente de IA usa o conteúdo extraído como referência primária na correção.

ALTER TABLE atividades
  ADD COLUMN IF NOT EXISTS gabarito_pdf_path TEXT,
  ADD COLUMN IF NOT EXISTS gabarito_pdf_content_type TEXT;
