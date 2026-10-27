// Opções do ECharts para cada gráfico. Cada função recebe os dados já calculados (d),
// o contexto do que está selecionado (ctx) e as cores do tema atual (t).
import { compacto, hora, horaDe, num, pct, sinal } from './formato.js';

const FONTE = 'system-ui, -apple-system, "Segoe UI", sans-serif';

export function tokens() {
  const css = getComputedStyle(document.documentElement);
  const v = nome => css.getPropertyValue(nome).trim();
  return {
    tinta: v('--tinta'), tinta2: v('--tinta-2'), tinta3: v('--tinta-3'),
    grade: v('--grade'), eixo: v('--eixo'), superficie: v('--superficie'), borda: v('--borda'),
    cor: { 13: v('--cor-13'), 22: v('--cor-22'), outros: v('--cor-outros'), alt: v('--cor-alt') },
    rampa: {
      13: [v('--rampa-13-1'), v('--rampa-13-2'), v('--rampa-13-3')],
      22: [v('--rampa-22-1'), v('--rampa-22-2'), v('--rampa-22-3')],
    },
    neutro: v('--neutro'),
  };
}

/** A cor segue o candidato (número), nunca a posição no ranking. */
export const corDe = (t, serie) => t.cor[serie] ?? (serie === 'outros' ? t.cor.outros : t.cor.alt);

function base(t, animar) {
  return {
    animation: animar,
    useUTC: true,
    textStyle: { fontFamily: FONTE, color: t.tinta2 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: t.eixo, width: 1, type: 'solid' } },
      backgroundColor: t.superficie, borderColor: t.borda, borderWidth: 1, padding: [8, 10],
      textStyle: { color: t.tinta, fontFamily: FONTE }, extraCssText: 'box-shadow:0 4px 16px rgba(0,0,0,.12);',
    },
  };
}

function eixoX(t, eixo, min, max, estreito) {
  const comum = {
    min, max, splitNumber: estreito ? 3 : 6,
    axisLine: { lineStyle: { color: t.eixo } }, axisTick: { show: false }, splitLine: { show: false },
    axisLabel: { color: t.tinta3, hideOverlap: true },
  };
  if (eixo === 'tempo') return { type: 'time', ...comum, axisLabel: { ...comum.axisLabel, formatter: '{HH}:{mm}' } };
  return { type: 'value', ...comum, axisLabel: { ...comum.axisLabel, formatter: v => `${v}%` } };
}

function eixoY(t, extra = {}) {
  return {
    type: 'value', axisLine: { show: false }, axisTick: { show: false },
    splitLine: { lineStyle: { color: t.grade, width: 1, type: 'solid' } },
    axisLabel: { color: t.tinta3 }, ...extra,
  };
}

function linhaMomento(t, x) {
  return {
    symbol: ['none', 'none'], silent: true, animation: false,
    label: { show: false }, lineStyle: { color: t.tinta2, width: 1, type: 'solid' },
    data: [{ xAxis: x }],
  };
}

function ponto(t, cor, coord, texto, posicao) {
  return {
    coord, symbol: 'circle', symbolSize: 10,
    itemStyle: { color: cor, borderColor: t.superficie, borderWidth: 2 },
    label: {
      show: true, position: posicao, distance: 8, formatter: texto,
      color: t.tinta, fontSize: 12, lineHeight: 16, backgroundColor: t.superficie, padding: [2, 4], borderRadius: 3,
    },
  };
}

// ---------- tooltip montado com DOM (nomes vêm de dados: nada de innerHTML) ----------

function caixaTooltip(titulo, linhas) {
  const caixa = document.createElement('div');
  caixa.className = 'tt';
  const h = document.createElement('div');
  h.className = 'tt__titulo';
  h.textContent = titulo;
  caixa.append(h);
  for (const { cor, valor, rotulo } of linhas) {
    const l = document.createElement('div');
    l.className = 'tt__linha';
    const chave = document.createElement('span');
    chave.className = 'tt__chave';
    if (cor) chave.style.background = cor;
    const v = document.createElement('strong');
    v.textContent = valor;
    const r = document.createElement('span');
    r.textContent = rotulo;
    l.append(chave, v, r);
    caixa.append(l);
  }
  return caixa;
}

const tituloMomento = (d, ctx, i) => `${hora(ctx.inicio, ctx.minutos[i])} · ${pct(d.xsUrnas[i])} das urnas`;

// ---------- 1. % dos votos válidos ao longo da apuração ----------

export function opcoesPercentual(t, d, ctx) {
  const xs = ctx.eixo === 'tempo' ? d.xsTempo : d.xsUrnas;
  const series = d.candidatos.map((c, k) => ({
    id: `p-${c}`, name: ctx.nomes[c], type: 'line', symbol: 'none', smooth: false, connectNulls: false,
    lineStyle: { width: 2, color: corDe(t, c), cap: 'round', join: 'round' }, itemStyle: { color: corDe(t, c) },
    emphasis: { disabled: true },
    data: d.p[c].map((y, i) => [xs[i], y]),
    endLabel: {
      show: !ctx.estreito, color: t.tinta, fontSize: 12, distance: 6,
      formatter: p => `${ctx.nomes[c]} ${pct(p.value[1])}`,
    },
    markLine: k === 0 ? linhaMomento(t, xs[ctx.i]) : undefined,
    markPoint: {
      silent: true, animation: false,
      data: d.L.eventos.viradas.filter(v => v.lider === c)
        .map(v => ponto(t, corDe(t, c), [xs[v.i], d.p[c][v.i]], `Virada · ${hora(ctx.inicio, ctx.minutos[v.i])}`, 'top')),
    },
  }));
  if (ctx.turno === 2) {
    series[0].markLine = {
      ...linhaMomento(t, xs[ctx.i]),
      data: [{ xAxis: xs[ctx.i] }, { yAxis: 50, lineStyle: { color: t.eixo, width: 1, type: 'solid' } }],
    };
  }
  return {
    ...base(t, ctx.animar),
    grid: { left: 48, right: ctx.estreito ? 16 : 150, top: 24, bottom: 64 },
    xAxis: eixoX(t, ctx.eixo, xs[0], xs[xs.length - 1], ctx.estreito),
    yAxis: eixoY(t, { scale: true, axisLabel: { color: t.tinta3, formatter: v => `${v}%` } }),
    dataZoom: [{
      type: 'slider', xAxisIndex: 0, filterMode: 'none', startValue: ctx.zoom[0], endValue: ctx.zoom[1],
      height: 22, bottom: 8, brushSelect: false, borderColor: t.grade, backgroundColor: 'transparent',
      fillerColor: 'rgba(137,135,129,0.16)', handleStyle: { color: t.superficie, borderColor: t.tinta3 },
      moveHandleStyle: { color: t.tinta3 }, textStyle: { color: t.tinta3 },
      dataBackground: { lineStyle: { color: t.eixo }, areaStyle: { color: t.grade } },
      selectedDataBackground: { lineStyle: { color: t.tinta3 }, areaStyle: { color: t.eixo } },
      labelFormatter: ctx.eixo === 'tempo' ? v => horaDe(v) : v => pct(v, 0),
    }],
    tooltip: {
      ...base(t).tooltip,
      formatter: ps => {
        const i = ps[0].dataIndex;
        const linhas = d.candidatos
          .map(c => ({ cor: corDe(t, c), valor: pct(d.p[c][i], 2), rotulo: ctx.nomes[c], ordem: d.p[c][i] ?? 0 }))
          .sort((x, y) => y.ordem - x.ordem);
        return caixaTooltip(tituloMomento(d, ctx, i), linhas);
      },
    },
    series,
  };
}

// ---------- 3. Ritmo: votos que entraram a cada janela de 10 min ----------

export function opcoesRitmo(t, d, ctx) {
  const { a, b } = d;
  const r = d.L.ritmo;
  const larg = ctx.largura * 60000;
  const x0 = d.xsTempo[0];
  const meio = k => x0 + k * larg + larg / 2;
  const area = [];
  for (const lado of [a, b]) {
    const arr = d.L.eventos.arrancada[lado];
    if (!arr) continue;
    area.push([
      {
        xAxis: x0 + arr.janela * larg, itemStyle: { color: corDe(t, lado), opacity: 0.1 },
        label: { show: !ctx.estreito, position: 'insideTop', color: t.tinta2, fontSize: 11, formatter: `Arrancada de\n${ctx.nomes[lado]}` },
      },
      { xAxis: x0 + (arr.janela + 1) * larg },
    ]);
  }
  const serie = (c, k) => ({
    id: `r-${c}`, name: ctx.nomes[c], type: 'bar', barMaxWidth: 12, barGap: '20%',
    itemStyle: { color: corDe(t, c), borderRadius: [4, 4, 0, 0] }, emphasis: { focus: 'none' },
    data: r[c].map((y, i) => [meio(i), y]),
    markArea: k === 0 ? { silent: true, data: area } : undefined,
    markLine: k === 0 ? linhaMomento(t, d.xsTempo[ctx.i]) : undefined,
  });
  return {
    ...base(t, ctx.animar),
    grid: { left: 64, right: 24, top: 24, bottom: 32 },
    xAxis: eixoX(t, 'tempo', ctx.zoomTempo[0], ctx.zoomTempo[1], ctx.estreito),
    yAxis: eixoY(t, { axisLabel: { color: t.tinta3, formatter: v => compacto(v) } }),
    tooltip: {
      ...base(t).tooltip,
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(137,135,129,0.12)' } },
      formatter: ps => {
        const k = ps[0].dataIndex;
        const de = x0 + k * larg;
        const linhas = [a, b].map(c => ({ cor: corDe(t, c), valor: num(r[c][k]), rotulo: ctx.nomes[c] }));
        const saldo = r[a][k] - r[b][k];
        linhas.push({ cor: null, valor: sinal(saldo), rotulo: `saldo para ${ctx.nomes[saldo >= 0 ? a : b]}` });
        linhas.push({ cor: null, valor: num(r.secoes[k]), rotulo: 'urnas recebidas' });
        return caixaTooltip(`${horaDe(de)}–${horaDe(de + larg)}`, linhas);
      },
    },
    series: [a, b].map(serie),
  };
}

// ---------- Pausa: comparecimento 1º × 2º turno e cenários ----------

function barrasHorizontais(t, ctx, series, eixoValor) {
  return {
    ...base(t, ctx.animar),
    grid: { left: ctx.estreito ? 8 : 300, right: 72, top: 8, bottom: 24, containLabel: ctx.estreito },
    xAxis: eixoY(t, eixoValor),
    yAxis: {
      type: 'category', inverse: true, data: ctx.rotulos, axisTick: { show: false },
      axisLine: { lineStyle: { color: t.eixo } },
      axisLabel: { color: t.tinta2, width: ctx.estreito ? 140 : 290, overflow: 'break', lineHeight: 15 },
    },
    tooltip: { ...base(t).tooltip, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(137,135,129,0.12)' } } },
    series,
  };
}

export function opcoesComparecimento(t, ctx) {
  const serie = (nome, valores, cor) => ({
    name: nome, type: 'bar', barMaxWidth: 12, barGap: '30%',
    itemStyle: { color: cor, borderRadius: [0, 4, 4, 0] },
    label: { show: true, position: 'right', color: t.tinta, fontSize: 12, formatter: p => pct(p.value, 1) },
    data: valores,
  });
  const min = Math.floor(Math.min(...ctx.t1, ...ctx.t2) / 5) * 5;
  const o = barrasHorizontais(t, ctx, [serie('1º turno', ctx.t1, t.eixo), serie('2º turno', ctx.t2, t.tinta2)],
    { min, max: 90, axisLabel: { color: t.tinta3, formatter: v => `${v}%` } });
  o.tooltip.valueFormatter = v => pct(v, 2);
  return o;
}

/** Votos registrados nos logs depois das 17h, a cada 10 min, no turno escolhido. */
export function opcoesLogs(t, ctx) {
  return {
    ...base(t, ctx.animar),
    grid: { left: 56, right: 16, top: 24, bottom: 32 },
    xAxis: {
      type: 'category', data: ctx.rotulos, axisTick: { show: false }, axisLine: { lineStyle: { color: t.eixo } },
      axisLabel: { color: t.tinta3, interval: ctx.valores.length > 16 ? (ctx.estreito ? 5 : 2) : (ctx.estreito ? 2 : 0) },
    },
    yAxis: eixoY(t, { axisLabel: { color: t.tinta3, formatter: v => (v >= 10000 ? compacto(v) : num(v)) } }),
    tooltip: {
      ...base(t).tooltip, axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(137,135,129,0.12)' } },
      valueFormatter: v => `${num(v)} votos`,
    },
    series: [{
      name: ctx.nome, type: 'bar', barMaxWidth: 24, itemStyle: { color: t.tinta2, borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', color: t.tinta, fontSize: 11, formatter: p => (p.value ? num(p.value) : '') },
      data: ctx.valores,
    }],
  };
}

export function opcoesCenarios(t, ctx) {
  const o = barrasHorizontais(t, ctx, [{
    name: ctx.nome ?? 'Vantagem de Lula', type: 'bar', barMaxWidth: 20,
    itemStyle: { color: ctx.cor, borderRadius: [0, 4, 4, 0] },
    label: { show: true, position: 'right', color: t.tinta, fontSize: 12, formatter: p => (p.value < 10000 ? num(p.value) : compacto(p.value)) },
    data: ctx.valores,
  }], { min: 0, axisLabel: { color: t.tinta3, formatter: v => compacto(v) } });
  o.tooltip.valueFormatter = v => `${ctx.prefixo ?? '+'}${num(v)} votos`;
  return o;
}

// ---------- 4. Mapa por UF: diferença em pontos percentuais dos válidos no momento ----------

export function opcoesMapa(t, ctx) {
  const { a, b } = ctx;
  const ramA = t.rampa[a] ?? t.rampa[13];
  const ramB = t.rampa[b] ?? t.rampa[22];
  return {
    animation: ctx.animar,
    textStyle: { fontFamily: FONTE, color: t.tinta2 },
    tooltip: {
      trigger: 'item', backgroundColor: t.superficie, borderColor: t.borda, padding: [8, 10],
      textStyle: { color: t.tinta, fontFamily: FONTE }, extraCssText: 'box-shadow:0 4px 16px rgba(0,0,0,.12);',
      formatter: p => {
        const u = ctx.porUf.atual[p.name];
        if (!u) return caixaTooltip(p.name, []);
        return caixaTooltip(`${u.nome} · ${pct(u.urnas)} das urnas`, [
          { cor: corDe(t, a), valor: pct(u.pa, 2), rotulo: ctx.nomes[a] },
          { cor: corDe(t, b), valor: pct(u.pb, 2), rotulo: ctx.nomes[b] },
          { cor: null, valor: sinal(u.votos), rotulo: 'votos de diferença' },
        ]);
      },
    },
    visualMap: {
      type: 'continuous', min: -ctx.escala, max: ctx.escala, calculable: false, realtime: false,
      orient: 'horizontal', left: 'center', bottom: 0, itemWidth: 12, itemHeight: ctx.estreito ? 120 : 220,
      text: ctx.estreito ? [ctx.nomes[a], ctx.nomes[b]] : [`${ctx.nomes[a]} à frente`, `${ctx.nomes[b]} à frente`], textGap: 8,
      textStyle: { color: t.tinta2, fontSize: 12 },
      inRange: { color: [...ramB].reverse().concat(t.neutro, ramA) },
    },
    series: [{
      type: 'map', map: 'BR', nameProperty: 'sigla', roam: false, top: 8, bottom: 48,
      selectedMode: false, label: { show: false },
      itemStyle: { borderColor: t.superficie, borderWidth: 1 },
      emphasis: { label: { show: false }, itemStyle: { borderColor: t.tinta, borderWidth: 1.5 } },
      data: Object.entries(ctx.porUf.atual).map(([uf, u]) => ({ name: uf, value: u.margem })),
    }],
  };
}
