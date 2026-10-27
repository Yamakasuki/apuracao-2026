// Formatação em pt-BR. Os horários do JSON são de Brasília e vêm sem fuso;
// tratamos tudo como UTC para o rótulo não mudar com o fuso de quem abre o site.
const inteiro = new Intl.NumberFormat('pt-BR');
const relogio = new Intl.DateTimeFormat('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit' });
const relogioDia = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'UTC', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
});

export const num = n => inteiro.format(n);

export const sinal = n => (n > 0 ? '+' : n < 0 ? '−' : '') + inteiro.format(Math.abs(n));

export function pct(x, casas = 1) {
  if (x == null || !Number.isFinite(x)) return '–';
  return x.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }) + '%';
}

export function compacto(n) {
  const a = Math.abs(n);
  const s = n < 0 ? '−' : '';
  if (a >= 1e6) return s + (a / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: a >= 1e7 ? 1 : 2 }) + ' mi';
  if (a >= 1e3) return s + Math.round(a / 1e3).toLocaleString('pt-BR') + ' mil';
  return s + inteiro.format(a);
}

/** Instante (ms) do minuto m da apuração. */
export const instante = (inicio, m) => Date.parse(inicio + 'Z') + m * 60000;

/** "18:44", ou "26/10, 08:12" quando já é outro dia. */
export function hora(inicio, m) {
  const t = instante(inicio, m);
  const mesmoDia = new Date(t).getUTCDate() === new Date(Date.parse(inicio + 'Z')).getUTCDate();
  return (mesmoDia ? relogio : relogioDia).format(t);
}

export const horaDe = t => relogio.format(t);
