import { test } from 'node:test';
import assert from 'node:assert/strict';
import { indiceAte, maisProximo, percentuais, vantagem, janela, normalizar, ranking } from '../docs/js/calculos.js';
import { compacto, hora, pct, sinal } from '../docs/js/formato.js';

const local = {
  secoes: [1, 3, 4],
  13: [10, 14, 20],
  22: [5, 28, 30],
  brancos: [1, 1, 2],
  nulos: [0, 2, 2],
};

test('indiceAte acha o último minuto já apurado', () => {
  assert.equal(indiceAte([0, 2, 5], 4), 1);
  assert.equal(indiceAte([0, 2, 5], 5), 2);
  assert.equal(indiceAte([3, 4], 1), -1);
});

test('maisProximo', () => {
  assert.equal(maisProximo([0, 10, 20], 14), 1);
  assert.equal(maisProximo([0, 10, 20], 16), 2);
  assert.equal(maisProximo([0, 10, 20], -5), 0);
});

test('percentuais dos válidos não contam brancos e nulos', () => {
  const p = percentuais(local, ['13', '22']);
  assert.equal(p['13'][0], (100 * 10) / 15);
  assert.equal(p['22'][2], 60);
});

test('percentual é null antes do primeiro voto válido', () => {
  const p = percentuais({ secoes: [0], 13: [0], 22: [0] }, ['13', '22']);
  assert.equal(p['13'][0], null);
});

test('vantagem e janela do período', () => {
  assert.deepEqual(vantagem(local, '13', '22'), [5, -14, -10]);
  assert.deepEqual(janela(local, ['13', '22'], 0, 2), { secoes: 3, 13: 10, 22: 25 });
  assert.deepEqual(janela(local, ['13'], -1, 0), { secoes: 1, 13: 10 });
});

test('normalizar tira acento e caixa', () => {
  assert.equal(normalizar('São PAULO'), 'sao paulo');
});

test('ranking por votos e por pontos, filtrando a UF', () => {
  const tabela = {
    colunas: ['uf', 'codigo', 'nome', 'aptos', 'comparecimento', '13', '22', 'brancos', 'nulos'],
    linhas: [
      ['SP', '1', 'GRANDE', 0, 0, 600, 400, 0, 0],
      ['SP', '2', 'PEQUENA', 0, 0, 90, 10, 0, 0],
      ['BA', '3', 'OUTRA', 0, 0, 900, 100, 0, 0],
      ['SP', '4', 'DO OUTRO', 0, 0, 10, 90, 0, 0],
    ],
  };
  const base = { lado: '13', outro: '22', candidatos: ['13', '22'] };
  assert.deepEqual(ranking(tabela, base).map(m => m.nome), ['OUTRA', 'GRANDE', 'PEQUENA']);
  assert.deepEqual(ranking(tabela, { ...base, uf: 'SP', por: 'pontos' }).map(m => m.nome), ['PEQUENA', 'GRANDE']);
  assert.deepEqual(ranking(tabela, { ...base, uf: 'SP', por: 'pontos', minimoValidos: 200 }).map(m => m.nome), ['GRANDE']);
  assert.deepEqual(ranking(tabela, { ...base, lado: '22', outro: '13' }).map(m => m.nome), ['DO OUTRO']);
});

test('formatos pt-BR', () => {
  assert.equal(pct(50.456, 2), '50,46%');
  assert.equal(pct(null), '–');
  assert.equal(sinal(-1234), '−1.234');
  assert.equal(compacto(2_345_678), '2,35 mi');
  assert.equal(compacto(-12_400), '−12 mil');
  assert.equal(hora('2026-10-25T17:00:00', 104), '18:44');
  assert.equal(hora('2026-10-25T17:00:00', 15 * 60 + 12), '26/10, 08:12');
});
