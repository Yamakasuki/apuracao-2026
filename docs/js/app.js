import { compacto, hora, horaDe, instante, num, pct, sinal } from './formato.js';
import { indiceAte, janela, maisProximo, normalizar, percentuais, ranking, vantagem } from './calculos.js';
import * as G from './graficos.js';

const UFS = {
  BR: 'Brasil (total)', AC: 'Acre', AL: 'Alagoas', AP: 'Amapá', AM: 'Amazonas', BA: 'Bahia', CE: 'Ceará',
  DF: 'Distrito Federal', ES: 'Espírito Santo', GO: 'Goiás', MA: 'Maranhão', MT: 'Mato Grosso',
  MS: 'Mato Grosso do Sul', MG: 'Minas Gerais', PA: 'Pará', PB: 'Paraíba', PR: 'Paraná', PE: 'Pernambuco',
  PI: 'Piauí', RJ: 'Rio de Janeiro', RN: 'Rio Grande do Norte', RS: 'Rio Grande do Sul', RO: 'Rondônia',
  RR: 'Roraima', SC: 'Santa Catarina', SP: 'São Paulo', SE: 'Sergipe', TO: 'Tocantins', ZZ: 'Exterior',
};
const IBGE = {
  11: 'RO', 12: 'AC', 13: 'AM', 14: 'RR', 15: 'PA', 16: 'AP', 17: 'TO', 21: 'MA', 22: 'PI', 23: 'CE', 24: 'RN',
  25: 'PB', 26: 'PE', 27: 'AL', 28: 'SE', 29: 'BA', 31: 'MG', 32: 'ES', 33: 'RJ', 35: 'SP', 41: 'PR', 42: 'SC',
  43: 'RS', 50: 'MS', 51: 'MT', 52: 'GO', 53: 'DF',
};

// Contexto que não está nos dados (fontes: Migalhas, Terra/Estadão e InfoMoney, cobertura de 25/10/2026).
const CONTEXTO = {
  '2026-2t': 'Por que a pausa das 17h às 19h no 2º turno: o ministro Cristiano Zanin (STF) prorrogou a votação até 19h ' +
    'nas seções ainda abertas, e o TSE suspendeu a totalização nesse intervalo. Os boletins só voltaram a ser recebidos às 19h.',
};

const $ = s => document.querySelector(s);
const el = (tag, cls, texto) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (texto != null) e.textContent = texto;
  return e;
};
const semMovimento = matchMedia('(prefers-reduced-motion: reduce)');

const estado = { id: null, local: 'BR', eixo: 'tempo', i: 0, periodo: null, timer: null, minutoPlayer: 0 };
const cache = new Map();
const graficos = {};
let D = null; // { resumo, linha, municipios }
let d = null; // derivados do local selecionado

async function json(caminho) {
  const r = await fetch(caminho);
  if (!r.ok) throw new Error(`${caminho}: HTTP ${r.status}`);
  return r.json();
}

// ---------- tema ----------
function lerTema() {
  try { return localStorage.getItem('tema'); } catch { return null; }
}
function aplicarTema(tema) {
  if (tema) document.documentElement.dataset.theme = tema;
}
$('#tema').addEventListener('click', () => {
  const escuro = getComputedStyle(document.documentElement).colorScheme.includes('dark');
  const novo = escuro ? 'light' : 'dark';
  aplicarTema(novo);
  try { localStorage.setItem('tema', novo); } catch {}
  desenharTudo();
});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => desenharTudo());

// ---------- dados ----------
async function carregarEleicao(id) {
  if (!cache.has(id)) {
    const p = `dados/${id}`;
    const [resumo, linha, municipios] = await Promise.all([
      json(`${p}/resumo.json`), json(`${p}/linha_do_tempo.json`), json(`${p}/municipios.json`),
    ]);
    cache.set(id, { resumo, linha, municipios });
  }
  D = cache.get(id);
  estado.id = id;
  if (!D.linha.locais[estado.local]) estado.local = 'BR';
  preencherLocais();
  estado.i = D.linha.minutos.length - 1;
  estado.periodo = null;
  desenharTudo();
}

const nomes = () => {
  const n = { outros: 'Outros', brancos: 'Brancos', nulos: 'Nulos' };
  for (const c of D.resumo.candidatos) n[c.numero] = nomeCurto(c.nome);
  return n;
};
const nomeCurto = nome => nome.toLowerCase().replace(/(^|\s)\p{L}/gu, s => s.toUpperCase());

function derivar() {
  const { linha, resumo } = D;
  const L = linha.locais[estado.local];
  const [a, b] = linha.principais;
  const candidatos = linha.series.filter(s => s !== 'brancos' && s !== 'nulos');
  const total = resumo.totais[estado.local].secoes;
  return {
    L, a, b, candidatos, total,
    xsTempo: linha.minutos.map(m => instante(linha.inicio, m)),
    xsUrnas: L.secoes.map(s => (100 * s) / total),
    p: percentuais(L, candidatos),
    v: vantagem(L, a, b),
  };
}

function ultimoIndice() { return D.linha.minutos.length - 1; }
function indice99() { return indiceAte(D.linha.minutos, D.linha.minuto_99); }

function periodo() {
  return estado.periodo ?? [0, estado.eixo === 'tempo' ? indice99() : ultimoIndice()];
}
const xs = () => (estado.eixo === 'tempo' ? d.xsTempo : d.xsUrnas);

function contexto() {
  const [i0, i1] = periodo();
  return {
    eixo: estado.eixo, i: estado.i, inicio: D.linha.inicio, minutos: D.linha.minutos, nomes: nomes(),
    turno: D.resumo.turno, largura: D.linha.largura_ritmo, animar: !semMovimento.matches, estreito: innerWidth < 600,
    zoom: [xs()[i0], xs()[i1]], zoomTempo: [d.xsTempo[i0], d.xsTempo[i1]],
  };
}

// ---------- filtros ----------
function preencherTurnos(eleicoes) {
  const s = $('#f-turno');
  for (const e of eleicoes) {
    const o = el('option', null, `${e.ano} · ${e.turno}º turno`);
    o.value = e.id;
    s.append(o);
  }
  s.addEventListener('change', () => carregarEleicao(s.value));
}

function preencherLocais() {
  const s = $('#f-local');
  s.replaceChildren();
  const locais = Object.keys(D.linha.locais).sort((x, y) => (x === 'BR' ? -1 : y === 'BR' ? 1 : (UFS[x] ?? x).localeCompare(UFS[y] ?? y)));
  for (const uf of locais) {
    const o = el('option', null, UFS[uf] ?? uf);
    o.value = uf;
    s.append(o);
  }
  s.value = estado.local;
}

function trocarLocal(uf) {
  estado.local = uf;
  $('#f-local').value = uf;
  desenharTudo();
}

$('#f-local').addEventListener('change', e => trocarLocal(e.target.value));
for (const r of document.querySelectorAll('input[name="eixo"]')) {
  r.addEventListener('change', () => { estado.eixo = r.value; estado.periodo = null; desenharGraficos(); renderPeriodo(); });
}

// ---------- player ----------
const slider = $('#momento');
slider.addEventListener('input', () => { parar(); definirMomento(Number(slider.value)); });
$('#play').addEventListener('click', () => (estado.timer ? parar() : tocar()));

function tocar() {
  const { minutos, minuto_99 } = D.linha;
  estado.minutoPlayer = estado.i >= ultimoIndice() ? -1 : minutos[estado.i];
  $('#play').textContent = '❚❚ Pausar';
  estado.timer = setInterval(() => {
    estado.minutoPlayer += Number($('#velocidade').value);
    if (estado.minutoPlayer > minuto_99) {
      definirMomento(ultimoIndice());
      return parar();
    }
    definirMomento(Math.max(0, indiceAte(minutos, estado.minutoPlayer)));
  }, 100);
}
function parar() {
  clearInterval(estado.timer);
  estado.timer = null;
  $('#play').textContent = '▶ Reproduzir';
}

function definirMomento(i) {
  estado.i = i;
  slider.value = i;
  atualizarMomento();
}

// ---------- desenho ----------
function grafico(id) {
  if (!graficos[id]) {
    graficos[id] = echarts.init($(`#${id}`), null, { renderer: 'canvas' });
    new ResizeObserver(() => graficos[id].resize()).observe($(`#${id}`));
  }
  return graficos[id];
}

function desenharTudo() {
  if (!D) return;
  d = derivar();
  slider.max = ultimoIndice();
  slider.value = estado.i;
  renderResultado();
  renderLegendas();
  desenharGraficos();
  desenharMapa();
  renderDestaques();
  renderRankings();
  renderBusca();
  renderPeriodo();
  atualizarMomento();
  renderNota();
  renderPausa();
}

// ---------- a pausa mudou o resultado? ----------
const ROTULO_GRUPO = { cidades: 'Salvador, Feira de Santana e Lauro de Freitas', resto_uf: 'Resto da Bahia', resto_br: 'Resto do Brasil' };
const ROTULO_CENARIO = {
  oficial: 'Resultado oficial',
  sem_excesso_todos_para_a: 'Sem os eleitores a mais (se todos tivessem votado em Lula)',
  excesso_todos_para_b: 'Eleitores a mais contados para Flávio (pior caso)',
  sem_cidades: 'Anulando todas as urnas das 3 cidades',
  sem_uf: 'Anulando a Bahia inteira',
};

// Contagem publicada pela imprensa a partir dos logs de todas as urnas (citada no texto do 1º turno).
const IMPRENSA = { 1: 3724999 }; // 1º turno: CNN Brasil (sem prorrogação, só para comparar)

let PAUSA = null; // docs/dados/2026-2t/pausa.json, carregado uma vez (o destaque não depende do turno escolhido lá em cima)
let turnoPausa = '2';

for (const r of document.querySelectorAll('input[name="turno-pausa"]')) {
  r.addEventListener('change', () => { turnoPausa = r.value; renderPausa(); renderTabelas(); });
}

function renderPausa() {
  const P = PAUSA;
  $('#pausa').hidden = !P;
  if (!P) return;
  const t2 = turnoPausa === '2';
  const sufixo = t2 ? '2t' : '1t';
  const taxa = g => (100 * g.comparecimento) / g.aptos;
  const margem = P.cenarios[0].margem;
  const cid = P.logs.cidades;
  const faixas = cid[`faixas_${sufixo}`];
  const depois = t2 ? cid.depois_2t : cid.depois_1t;
  const votos = t2 ? cid.votos_2t : cid.votos_1t;
  const depois1710 = faixas.slice(1).reduce((a, b) => a + b, 0);
  const brasil = IMPRENSA[turnoPausa];

  const B = P.brasil_apos_17h; // todas as urnas do país (apolinario/urnas-tardias, conferido urna por urna)
  $('#pausa-veredito').textContent = t2
    ? `Não. Em todas as urnas do país, ${num(B.brasil)} pessoas votaram depois das 17h, e só ${num(B.votos_estendidas)} delas em urnas ` +
      `que de fato usaram a prorrogação. Mesmo contando os ${num(B.brasil)} e passando todos de Lula para Flávio Bolsonaro, ` +
      `Lula ainda venceria por ${num(margem - 2 * B.brasil)} votos.`
    : `No 1º turno não houve prorrogação. Os ${num(brasil)} votos depois das 17h são de quem já estava na fila às 17h, o que acontece em toda eleição.`;

  const kpis = $('#pausa-kpis');
  kpis.replaceChildren();
  const kpi = (rotulo, valor, detalhe) => {
    const k = el('div', 'kpi');
    k.append(el('div', 'kpi__rotulo', rotulo), el('div', 'kpi__valor', valor));
    if (detalhe) k.append(el('div', 'kpi__detalhe', detalhe));
    kpis.append(k);
  };
  if (t2) {
    kpi('Votos depois das 17h no Brasil', num(B.brasil), `${pct((100 * B.brasil) / margem, 2)} da vantagem de Lula (todas as urnas)`);
    kpi('Urnas que usaram a prorrogação', num(B.estendidas), `${pct((100 * B.estendidas) / B.urnas, 2)} das urnas (fecharam depois das 17h45)`);
    kpi('Votos depois das 17h nessas urnas', num(B.votos_estendidas), `${pct((100 * B.votos_estendidas) / margem, 2)} da vantagem de Lula`);
    kpi('Vantagem de Lula', num(margem), 'votos, resultado oficial');
  } else {
    kpi('Votos depois das 17h no Brasil', num(brasil), 'CNN Brasil, logs das urnas');
    kpi('Nas 3 cidades da Bahia, depois das 17h', num(depois), `${pct((100 * depois) / votos, 2)} dos votos dessas cidades`);
    kpi('Nas 3 cidades, depois das 17h10', num(depois1710), 'fila do 1º turno, sem prorrogação');
  }

  $('#pausa-logs').textContent = t2
    ? `Cada urna guarda um log com o horário de cada voto, a hora em que abriu e a hora em que encerrou. Somando todas as ${num(B.urnas)} urnas do país, ` +
      `${num(B.brasil)} pessoas votaram depois das 17h (${pct((100 * B.brasil) / B.votos_total, 3)} dos votos). A maioria é o fim da fila de quem já estava no local ` +
      `às 17h, o que acontece em toda eleição: a urna registra esses votos e fecha logo depois. Só ${num(B.estendidas)} urnas ficaram abertas além das 17h45, ` +
      `ou seja, usaram a prorrogação, e nelas entraram ${num(B.votos_estendidas)} votos depois das 17h. O gráfico mostra como o número cai conforme o critério de "urna estendida".`
    : `Nas mesmas urnas de Salvador, Feira de Santana e Lauro de Freitas, no 1º turno, ${num(depois)} votos foram registrados depois das 17h ` +
      `(${pct((100 * depois) / votos, 2)} dos votos), ${num(depois1710)} deles depois das 17h10. Eram eleitores na fila: no 1º turno se votava em 5 cargos e a votação demorava mais.`;
  $('#pausa-grafico-legenda').textContent = t2
    ? 'no Brasil inteiro, conforme a hora em que a urna encerrou (sem o exterior)'
    : 'nas urnas de Salvador, Feira de Santana e Lauro de Freitas, a cada 10 minutos (1º turno)';
  const am = P.logs.amostra_brasil;
  $('#pausa-brasil').textContent = t2
    ? `E onde a prorrogação foi pedida? Nas ${num(cid.urnas)} urnas de Salvador, Feira de Santana e Lauro de Freitas, li o log de cada uma: ` +
      `${num(depois)} votos depois das 17h (${pct((100 * depois) / votos, 2)} dos votos dessas cidades). ${num(cid.estendidas)} urnas usaram a prorrogação, ` +
      `com ${num(cid.votos_estendidas)} votos depois das 17h; o último foi às ${cid.ultimo_2t.slice(0, 5)}.`
    : `Na amostra aleatória de ${num(am.urnas)} urnas do resto do país, ${num(am.depois_1t)} votos foram dados depois do fechamento no 1º turno.`;

  const ap = P.antes_da_pausa;
  $('#pausa-t1').textContent = `Antes da pausa tinham chegado só ${num(ap.secoes)} de ${num(ap.total_secoes)} boletins ` +
    `(${pct((100 * ap.secoes) / ap.total_secoes, 1)}), a maioria do exterior. Os outros ${pct((100 * (ap.total_secoes - ap.secoes)) / ap.total_secoes, 1)} ` +
    'chegaram depois das 19h, no Brasil inteiro. Ou seja, "as urnas apuradas depois da pausa" são praticamente todas as urnas do país: a pausa atrasou ' +
    'a contagem, mas a ordem de chegada não muda a soma final.';
  const c1 = taxa(P.turno1.cidades);
  const c2 = taxa(P.turno2.cidades);
  const r1 = taxa(P.turno1.resto_br);
  const r2 = taxa(P.turno2.resto_br);
  const pontos = x => x.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
  $('#pausa-t2').textContent = `Nas três cidades, o comparecimento foi de ${pct(c1, 2)} para ${pct(c2, 2)} (+${pontos(c2 - c1)} pontos), ` +
    `contra +${pontos(r2 - r1)} no resto do Brasil. Como os logs mostram que quase ninguém votou depois das 17h, ` +
    'essa alta aconteceu no horário normal (o TRE-BA mandou liberar os ônibus durante o dia). Mesmo contando tudo como efeito do caso, ' +
    `são uns ${num(P.excesso)} eleitores: ${pct((100 * P.excesso) / margem, 1)} da vantagem.`;
  $('#pausa-t3').textContent = `O cenário mais duro, anular a Bahia inteira (${num(P.turno2.cidades.secoes + P.turno2.resto_uf.secoes)} urnas), ` +
    `ainda deixa Lula ${num(P.cenarios.find(c => c.id === 'sem_uf').margem)} votos à frente.`;
  $('#pausa-limite').textContent = 'Como foi medido: o log registra o horário de cada voto pelo relógio da urna, convertido para Brasília pelo fuso de cada ' +
    'município (descoberto pela hora em que as urnas abriram). Nas três cidades li todas as urnas; o Brasil inteiro vem do repositório ' +
    'apolinario/urnas-tardias, que leu todas, com o mesmo método. Scripts: pipeline/logs_urna.py e pipeline/pausa.py.';

  const t = G.tokens();
  if (t2) {
    const rot = { '17:00': 'Todas as urnas', '17:15': 'Urnas que fecharam depois das 17h15', '17:30': 'Urnas que fecharam depois das 17h30', '17:45': 'Urnas que fecharam depois das 17h45' };
    grafico('g-logs').setOption(G.opcoesCenarios(t, {
      rotulos: B.cortes.map(c => `${rot[c.corte]} (${num(c.urnas)})`), valores: B.cortes.map(c => c.votos), cor: t.tinta2,
      animar: !semMovimento.matches, estreito: innerWidth < 600, nome: 'Votos depois das 17h', prefixo: '',
    }), true);
  } else {
    grafico('g-logs').setOption(G.opcoesLogs(t, {
      rotulos: faixas.map((_, k) => (k === faixas.length - 1 ? '19h20+' : `${17 + Math.floor(k / 6)}h${String((k % 6) * 10).padStart(2, '0')}`)),
      valores: faixas, nome: '1º turno', animar: !semMovimento.matches, estreito: innerWidth < 600,
    }), true);
  }

  const grupos = ['cidades', 'resto_uf', 'resto_br'];
  const legenda = $('#legenda-comp');
  legenda.replaceChildren();
  for (const [rot, cor] of [['1º turno', t.eixo], ['2º turno', t.tinta2]]) {
    const li = el('li');
    li.append(chave(cor, 'chave chave--barra'), rot);
    legenda.append(li);
  }
  grafico('g-comparecimento').setOption(G.opcoesComparecimento(t, {
    rotulos: grupos.map(g => ROTULO_GRUPO[g]), t1: grupos.map(g => taxa(P.turno1[g])), t2: grupos.map(g => taxa(P.turno2[g])),
    animar: !semMovimento.matches, estreito: innerWidth < 600,
  }), true);
  grafico('g-cenarios').setOption(G.opcoesCenarios(t, {
    rotulos: P.cenarios.map(c => ROTULO_CENARIO[c.id]), valores: P.cenarios.map(c => c.margem), cor: G.corDe(t, P.a),
    animar: !semMovimento.matches, estreito: innerWidth < 600,
  }), true);
}

function desenharGraficos() {
  const t = G.tokens();
  const ctx = contexto();
  grafico('g-percentual').setOption(G.opcoesPercentual(t, d, ctx), true);
  grafico('g-ritmo').setOption(G.opcoesRitmo(t, d, ctx), true);
  renderTabelas();
}

function ligarZoom() {
  graficos['g-percentual'].on('datazoom', () => {
    const z = graficos['g-percentual'].getOption().dataZoom[0];
    const x = xs();
    estado.periodo = [maisProximo(x, z.startValue), maisProximo(x, z.endValue)];
    const [i0, i1] = estado.periodo;
    graficos['g-ritmo'].setOption({ xAxis: { min: d.xsTempo[i0], max: d.xsTempo[i1] } });
    renderPeriodo();
  });
}

function atualizarMomento() {
  const i = estado.i;
  const x = xs();
  const t = G.tokens();
  const p = graficos['g-percentual'];
  if (p) {
    const extra = D.resumo.turno === 2 ? [{ yAxis: 50, lineStyle: { color: t.eixo, width: 1, type: 'solid' } }] : [];
    p.setOption({ series: [{ id: `p-${d.candidatos[0]}`, markLine: { data: [{ xAxis: x[i] }, ...extra] } }] });
    graficos['g-ritmo'].setOption({ series: [{ id: `r-${d.a}`, markLine: { data: [{ xAxis: d.xsTempo[i] }] } }] });
  }
  $('#momento-rotulo').textContent = `${hora(D.linha.inicio, D.linha.minutos[i])} · ${pct(d.xsUrnas[i], 1)}`;
  renderPlacar();
  atualizarMapa();
}

// ---------- blocos de texto ----------
function chave(cor, cls = 'chave') {
  const c = el('span', cls);
  c.style.setProperty('--cor', cor);
  c.style.background = cor;
  return c;
}

function renderResultado() {
  const n = nomes();
  const tot = D.resumo.totais[estado.local];
  const t = G.tokens();
  const cand = d.candidatos.filter(c => c !== 'outros').map(c => ({ c, v: tot[c] })).sort((x, y) => y.v - x.v);
  const validos = d.candidatos.reduce((s, c) => s + tot[c], 0);
  const [p1, p2] = cand;
  const sec = $('#resultado');
  sec.replaceChildren();
  const onde = estado.local === 'BR' ? 'no Brasil' : UFS[estado.local] === 'Exterior' ? 'no exterior' : `em ${UFS[estado.local]}`;
  sec.append(el('p', 'heroi__rotulo', `Mais votado ${onde} · ${D.resumo.ano}, ${D.resumo.turno}º turno`));
  const v = el('p', 'heroi__valor');
  v.append(chave(G.corDe(t, p1.c)), `${n[p1.c]} · ${pct((100 * p1.v) / validos, 2)}`);
  sec.append(v);
  sec.append(el('p', 'heroi__detalhe',
    `dos votos válidos: ${num(p1.v)} votos, ${num(p1.v - p2.v)} a mais que ${n[p2.c]} (${pct((100 * p2.v) / validos, 2)}).`));
  const kpis = el('div', 'kpis');
  const item = (rotulo, valor) => {
    const k = el('div', 'kpi');
    k.append(el('div', 'kpi__rotulo', rotulo), el('div', 'kpi__valor', valor));
    kpis.append(k);
  };
  item('Comparecimento', `${pct((100 * tot.comparecimento) / tot.aptos)} dos aptos`);
  item('Abstenção', compacto(tot.abstencoes));
  item('Brancos', compacto(tot.brancos));
  item('Nulos', compacto(tot.nulos));
  item('Urnas', num(tot.secoes));
  sec.append(kpis);
}

function renderLegendas() {
  const t = G.tokens();
  const n = nomes();
  for (const [id, lista, cls] of [['#legenda-p', d.candidatos, 'chave'], ['#legenda-r', [d.a, d.b], 'chave chave--barra']]) {
    const ul = $(id);
    ul.replaceChildren();
    for (const c of lista) {
      const li = el('li');
      li.append(chave(G.corDe(t, c), cls), n[c]);
      ul.append(li);
    }
  }
}

function renderPlacar() {
  const i = estado.i;
  const n = nomes();
  const t = G.tokens();
  const box = $('#placar');
  box.replaceChildren();
  const bloco = (rotulo, valor, cor) => {
    const b = el('div');
    if (cor) b.style.setProperty('--cor', cor);
    b.append(el('small', null, rotulo), el('strong', null, valor));
    box.append(b);
  };
  bloco(hora(D.linha.inicio, D.linha.minutos[i]), `${pct(d.xsUrnas[i], 2)} das urnas`);
  for (const c of [d.a, d.b]) bloco(`${n[c]} · ${num(d.L[c][i])} votos`, pct(d.p[c][i], 2), G.corDe(t, c));
  const v = d.v[i];
  bloco('Vantagem', v === 0 ? 'empate' : `${n[v > 0 ? d.a : d.b]} +${num(Math.abs(v))}`, v ? G.corDe(t, v > 0 ? d.a : d.b) : null);
}

/** Os 4 eventos mais relevantes do local: viradas, resultado garantido, picos (menos o placar final) e arrancadas. */
function renderDestaques() {
  const n = nomes();
  const t = G.tokens();
  const ev = d.L.eventos;
  const ultimo = d.v.length - 1;
  const m = i => `${hora(D.linha.inicio, D.linha.minutos[i])}, com ${pct(d.xsUrnas[i])} das urnas`;
  const cards = [];
  if (ev.viradas.length) {
    for (const v of ev.viradas) cards.push(['Virada', G.corDe(t, v.lider), `${n[v.lider]} passou à frente às ${m(v.i)}.`, v.i]);
  } else {
    const lider = d.v[ultimo] >= 0 ? d.a : d.b;
    cards.push(['Virada', G.corDe(t, lider), `Não houve: ${n[lider]} liderou do começo ao fim.`, null]);
  }
  if (ev.definido != null && D.resumo.turno === 2) {
    cards.push(['Resultado garantido', null, `Às ${m(ev.definido)}: a vantagem passou do total de eleitores das urnas que ainda faltavam.`, ev.definido]);
  }
  for (const lado of [d.a, d.b]) {
    const i = ev.pico[lado];
    // o pico no último minuto é só o resultado final, que já aparece no topo
    if (i != null && i !== ultimo) cards.push([`Maior vantagem de ${n[lado]}`, G.corDe(t, lado), `${num(Math.abs(d.v[i]))} votos às ${m(i)}.`, i]);
  }
  for (const lado of [d.a, d.b]) {
    const arr = ev.arrancada[lado];
    if (!arr) continue;
    const de = instante(D.linha.inicio, arr.janela * D.linha.largura_ritmo);
    const ate = de + D.linha.largura_ritmo * 60000;
    const ufs = arr.ufs?.length ? `, puxada por ${arr.ufs.map(([uf]) => uf).join(', ')}` : '';
    cards.push([`Maior arrancada de ${n[lado]}`, G.corDe(t, lado), `+${num(arr.liquido)} votos de vantagem entre ${horaDe(de)} e ${horaDe(ate)}${ufs}.`,
      indiceAte(D.linha.minutos, (arr.janela + 1) * D.linha.largura_ritmo - 1)]);
  }

  const box = $('#destaques');
  box.replaceChildren();
  document.querySelector('.contexto')?.remove();
  for (const [titulo, cor, texto, i] of cards.slice(0, 4)) {
    const c = el('div', 'destaque');
    const h = el('div', 'destaque__titulo');
    if (cor) h.append(chave(cor));
    h.append(titulo);
    c.append(h, el('p', null, texto));
    if (i != null) {
      const btn = el('button', 'botao botao--leve', 'Ver no gráfico');
      btn.type = 'button';
      btn.addEventListener('click', () => { parar(); definirMomento(i); $('#g-percentual').scrollIntoView({ block: 'center' }); });
      c.append(btn);
    }
    box.append(c);
  }
  if (CONTEXTO[estado.id]) box.after(el('p', 'nota contexto', CONTEXTO[estado.id]));
}

function renderPeriodo() {
  const [i0, i1] = periodo();
  const n = nomes();
  const j = janela(d.L, [d.a, d.b], i0 - 1, i1);
  const saldo = j[d.a] - j[d.b];
  $('#periodo').textContent = `No período ${hora(D.linha.inicio, D.linha.minutos[i0])}–${hora(D.linha.inicio, D.linha.minutos[i1])} ` +
    `entraram ${num(j.secoes)} urnas: ${n[d.a]} ${sinal(j[d.a])}, ${n[d.b]} ${sinal(j[d.b])} ` +
    `(saldo de ${num(Math.abs(saldo))} para ${n[saldo >= 0 ? d.a : d.b]}).`;
}

function renderNota() {
  const r = D.resumo;
  $('#nota-dados').textContent = `Dados processados em ${r.gerado_em.replace('T', ' ')}. ` +
    (r.secoes_sem_horario ? `${num(r.secoes_sem_horario)} urnas sem horário de recebimento entram nos totais, mas não na linha do tempo. ` : '') +
    'BUs recebidos antes das 17h (exterior) aparecem no primeiro minuto.';
}

// ---------- mapa ----------
function porUf(i) {
  const s = {};
  for (const [uf, L] of Object.entries(D.linha.locais)) {
    if (uf === 'BR' || uf === 'ZZ') continue;
    const validos = d.candidatos.reduce((acc, c) => acc + L[c][i], 0);
    const pa = validos ? (100 * L[d.a][i]) / validos : null;
    const pb = validos ? (100 * L[d.b][i]) / validos : null;
    s[uf] = { nome: UFS[uf], urnas: (100 * L.secoes[i]) / D.resumo.totais[uf].secoes, pa, pb, margem: validos ? pa - pb : 0, votos: L[d.a][i] - L[d.b][i] };
  }
  return s;
}

function escalaMapa() {
  const f = porUf(ultimoIndice());
  return Math.max(10, Math.ceil(Math.max(...Object.values(f).map(u => Math.abs(u.margem))) / 10) * 10);
}

// O tooltip do mapa lê este objeto, que muda a cada momento sem redesenhar o mapa.
const mapaPorUf = { atual: {} };

function desenharMapa() {
  mapaPorUf.atual = porUf(estado.i);
  const ctx = { a: d.a, b: d.b, nomes: nomes(), animar: !semMovimento.matches, estreito: innerWidth < 600, escala: escalaMapa(), porUf: mapaPorUf };
  grafico('g-mapa').setOption(G.opcoesMapa(G.tokens(), ctx), true);
}

function atualizarMapa() {
  const m = graficos['g-mapa'];
  if (!m) return;
  const f = porUf(estado.i);
  mapaPorUf.atual = f;
  m.setOption({ series: [{ data: Object.entries(f).map(([uf, u]) => ({ name: uf, value: u.margem })) }] });
  if ($('details[data-tabela="ufs"]').open) renderTabela('ufs');
}

// ---------- municípios ----------
function renderRankings() {
  const n = nomes();
  const t = G.tokens();
  const por = $('#ordem').value;
  const box = $('#rankings');
  box.replaceChildren();
  for (const [lado, outro] of [[d.a, d.b], [d.b, d.a]]) {
    const col = el('div');
    const h = el('h3');
    h.append(chave(G.corDe(t, lado)), `Mais vantagem para ${n[lado]}`);
    const ol = el('ol');
    for (const m of ranking(D.municipios, { uf: estado.local, lado, outro, candidatos: d.candidatos, por })) {
      const li = el('li', null, `${nomeCurto(m.nome)} (${m.uf}) `);
      li.append(el('small', null, por === 'votos' ? `+${num(m.votos)} votos` : `+${pct(m.pontos)} · ${num(m.validos)} válidos`));
      ol.append(li);
    }
    if (!ol.children.length) ol.append(el('li', null, 'Nenhum município.'));
    col.append(h, ol);
    box.append(col);
  }
}

function renderBusca() {
  const q = normalizar($('#busca').value.trim());
  const box = $('#busca-resultado');
  box.replaceChildren();
  if (q.length < 2) return;
  const col = Object.fromEntries(D.municipios.colunas.map((c, i) => [c, i]));
  const n = nomes();
  const achados = D.municipios.linhas.filter(l => normalizar(l[col.nome]).includes(q)).slice(0, 15);
  const linhas = achados.map(l => {
    const validos = d.candidatos.reduce((s, c) => s + l[col[c]], 0);
    return [`${nomeCurto(l[col.nome])} (${l[col.uf]})`, pct((100 * l[col[d.a]]) / validos, 2), pct((100 * l[col[d.b]]) / validos, 2),
      sinal(l[col[d.a]] - l[col[d.b]]), num(l[col.comparecimento])];
  });
  box.append(tabela(['Cidade', n[d.a], n[d.b], `Diferença (${n[d.a]} − ${n[d.b]})`, 'Comparecimento'], linhas.length ? linhas : [['Nada encontrado', '', '', '', '']]));
}
$('#ordem').addEventListener('change', renderRankings);
$('#busca').addEventListener('input', renderBusca);

// ---------- tabelas (equivalente acessível de cada gráfico) ----------
function tabela(cabecalho, linhas) {
  const t = el('table');
  const tr = el('tr');
  for (const c of cabecalho) tr.append(el('th', null, c));
  t.append(el('thead'));
  t.tHead.append(tr);
  const tb = el('tbody');
  for (const l of linhas) {
    const r = el('tr');
    for (const c of l) r.append(el('td', null, c));
    tb.append(r);
  }
  t.append(tb);
  return t;
}

function renderTabela(qual) {
  const det = $(`details[data-tabela="${qual}"]`);
  const box = det.querySelector('div');
  const n = nomes();
  const ini = D.linha.inicio;
  let cab;
  let linhas = [];
  if (qual === 'percentual') {
    cab = ['Horário', '% das urnas', ...d.candidatos.map(c => n[c]), 'Vantagem'];
    let proximo = -1;
    D.linha.minutos.forEach((m, i) => {
      if (m < proximo && i !== ultimoIndice()) return;
      proximo = m + 10;
      linhas.push([hora(ini, m), pct(d.xsUrnas[i], 2), ...d.candidatos.map(c => pct(d.p[c][i], 2)), sinal(d.v[i])]);
    });
  } else if (qual === 'ritmo') {
    cab = ['Janela', 'Urnas', n[d.a], n[d.b], 'Saldo'];
    const r = d.L.ritmo;
    linhas = r.secoes.map((s, k) => {
      const de = instante(ini, k * D.linha.largura_ritmo);
      return [`${horaDe(de)}–${horaDe(de + D.linha.largura_ritmo * 60000)}`, num(s), num(r[d.a][k]), num(r[d.b][k]), sinal(r[d.a][k] - r[d.b][k])];
    });
  } else if (qual === 'comparecimento') {
    cab = ['Grupo', '1º turno', '2º turno', 'Alta (pontos)', 'Urnas'];
    const taxa = g => (100 * g.comparecimento) / g.aptos;
    linhas = ['cidades', 'resto_uf', 'resto_br', 'brasil'].map(g => [ROTULO_GRUPO[g] ?? 'Brasil', pct(taxa(PAUSA.turno1[g]), 2),
      pct(taxa(PAUSA.turno2[g]), 2), (taxa(PAUSA.turno2[g]) - taxa(PAUSA.turno1[g])).toLocaleString('pt-BR', { maximumFractionDigits: 2 }), num(PAUSA.turno2[g].secoes)]);
  } else if (qual === 'logs') {
    if (turnoPausa === '2') {
      cab = ['Urnas consideradas', 'Urnas', 'Votos depois das 17h'];
      linhas = PAUSA.brasil_apos_17h.cortes.map(c => [c.corte === '17:00' ? 'Todas' : `Fecharam depois das ${c.corte}`, num(c.urnas), num(c.votos)]);
    } else {
      const f = PAUSA.logs.cidades.faixas_1t;
      cab = ['A partir de', 'Votos nas 3 cidades (1º turno)'];
      linhas = f.map((v, k) => [`${17 + Math.floor(k / 6)}h${String((k % 6) * 10).padStart(2, '0')}`, num(v)]);
    }
  } else if (qual === 'cenarios') {
    cab = ['Cenário', `Vantagem de ${n[PAUSA.a]}`];
    linhas = PAUSA.cenarios.map(c => [ROTULO_CENARIO[c.id], sinal(c.margem)]);
  } else {
    cab = ['Estado', '% das urnas', n[d.a], n[d.b], 'Diferença (pontos)', 'Diferença (votos)'];
    const i = estado.i;
    for (const [uf, L] of Object.entries(D.linha.locais)) {
      if (uf === 'BR') continue;
      const validos = d.candidatos.reduce((s, c) => s + L[c][i], 0);
      const pa = validos ? (100 * L[d.a][i]) / validos : null;
      const pb = validos ? (100 * L[d.b][i]) / validos : null;
      linhas.push([UFS[uf] ?? uf, pct((100 * L.secoes[i]) / D.resumo.totais[uf].secoes), pct(pa, 2), pct(pb, 2),
        validos ? (pa - pb).toLocaleString('pt-BR', { maximumFractionDigits: 1, signDisplay: 'always' }) : '–', sinal(L[d.a][i] - L[d.b][i])]);
    }
    linhas.sort((x, y) => x[0].localeCompare(y[0]));
  }
  box.replaceChildren(tabela(cab, linhas));
}

function renderTabelas() {
  for (const det of document.querySelectorAll('details[data-tabela]')) if (det.open) renderTabela(det.dataset.tabela);
}
for (const det of document.querySelectorAll('details[data-tabela]')) {
  det.addEventListener('toggle', () => det.open && D && renderTabela(det.dataset.tabela));
}

// gráficos dentro de um <details> fechado nascem com tamanho zero: redimensiona ao abrir
document.querySelector('details.mais').addEventListener('toggle', () => {
  for (const id of ['g-comparecimento', 'g-cenarios']) graficos[id]?.resize();
});

// ---------- início ----------
async function iniciar() {
  aplicarTema(lerTema());
  try {
    const [eleicoes, geo, pausa] = await Promise.all([
      json('dados/eleicoes.json'), json('dados/geo/uf.json'), json('dados/2026-2t/pausa.json').catch(() => null),
    ]);
    PAUSA = pausa;
    for (const f of geo.features) f.properties.sigla = IBGE[f.properties.codarea];
    echarts.registerMap('BR', geo);
    preencherTurnos(eleicoes);
    await carregarEleicao(eleicoes[0].id);
    ligarZoom();
    graficos['g-mapa'].on('click', p => p.name && trocarLocal(p.name));
  } catch (e) {
    $('#resultado').replaceChildren(el('p', null, `Não deu para carregar os dados (${e.message}). Rode o pipeline antes: veja o README.`));
    console.error(e);
  }
}
iniciar();
