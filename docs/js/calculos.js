// Contas simples sobre os acumulados do linha_do_tempo.json. Sem DOM, para testar com node --test.
// Os eventos (viradas, picos, arrancadas) já vêm prontos do pipeline em Python.

/** Último índice i com minutos[i] <= m (busca binária); -1 se nenhum. */
export function indiceAte(minutos, m) {
  let lo = 0;
  let hi = minutos.length - 1;
  let r = -1;
  while (lo <= hi) {
    const meio = (lo + hi) >> 1;
    if (minutos[meio] <= m) {
      r = meio;
      lo = meio + 1;
    } else hi = meio - 1;
  }
  return r;
}

/** Índice cujo valor em `xs` (crescente) é o mais próximo de x. */
export function maisProximo(xs, x) {
  let lo = 0;
  let hi = xs.length - 1;
  while (lo < hi) {
    const meio = (lo + hi) >> 1;
    if (xs[meio] < x) lo = meio + 1;
    else hi = meio;
  }
  return lo > 0 && Math.abs(xs[lo - 1] - x) <= Math.abs(xs[lo] - x) ? lo - 1 : lo;
}

/** Votos válidos (só candidatos, sem brancos e nulos) acumulados no índice i. */
export const validosEm = (local, candidatos, i) => candidatos.reduce((s, c) => s + local[c][i], 0);

/** % dos válidos de cada candidato em cada índice (null enquanto não há voto). */
export function percentuais(local, candidatos) {
  const n = local.secoes.length;
  const saida = Object.fromEntries(candidatos.map(c => [c, new Array(n)]));
  for (let i = 0; i < n; i++) {
    const v = validosEm(local, candidatos, i);
    for (const c of candidatos) saida[c][i] = v ? (100 * local[c][i]) / v : null;
  }
  return saida;
}

export const vantagem = (local, a, b) => local[a].map((x, i) => x - local[b][i]);

/** O que entrou depois do índice i0 até o índice i1 (inclusive). i0 = -1 pega desde o começo. */
export function janela(local, series, i0, i1) {
  const r = {};
  for (const s of ['secoes', ...series]) r[s] = local[s][i1] - (i0 >= 0 ? local[s][i0] : 0);
  return r;
}

export const normalizar = t => t.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();

/**
 * Municípios onde `lado` teve mais vantagem sobre `outro`.
 * por = 'votos' (diferença em votos) ou 'pontos' (diferença em pontos percentuais dos válidos).
 */
export function ranking(tabela, { uf = 'BR', lado, outro, candidatos, por = 'votos', n = 10, minimoValidos = 0 }) {
  const col = Object.fromEntries(tabela.colunas.map((c, i) => [c, i]));
  const saida = [];
  for (const l of tabela.linhas) {
    if (uf !== 'BR' && l[col.uf] !== uf) continue;
    const validos = candidatos.reduce((s, c) => s + l[col[c]], 0);
    const votos = l[col[lado]] - l[col[outro]];
    if (votos <= 0 || validos < minimoValidos) continue;
    saida.push({ uf: l[col.uf], nome: l[col.nome], votos, pontos: (100 * votos) / validos, validos });
  }
  return saida.sort((x, y) => y[por] - x[por]).slice(0, n);
}
