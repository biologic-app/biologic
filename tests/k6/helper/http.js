// lib/http_logger.js — враппер над k6/http с логированием запросов и ответов
//
// Переменные окружения:
//   LOG_HTTP=0           — отключить логирование полностью (по умолчанию включено)
//   LOG_ONLY_UNEXPECTED=0— логировать ВСЕ запросы, а не только неожиданные (по умолчанию включено, т.е. только неожиданные)
//   LOG_REQ_BODY=0       — не логировать тело запроса
//   LOG_RES_BODY=0       — не логировать тело ответа
//   LOG_HEADERS=0        — не логировать заголовки запроса (по умолчанию включено)
//   LOG_AUTH_FULL=1      — показывать Authorization целиком (по умолчанию маскируется)
//   LOG_MAX_BODY=500     — макс. символов тела (по умолчанию 500)
//
// Что значит "неожиданный" запрос/ответ:
//   По умолчанию ожидаемым считается любой ответ со статусом 2xx.
//   Если нужно явно пометить, какой статус ожидается для конкретного вызова
//   (например, тест намеренно бьёт по эндпоинту без токена и ждёт 401),
//   передайте поле expectedStatus в params — число или массив чисел:
//
//     http.get(url, { headers, expectedStatus: 401 });
//     http.post(url, body, { headers, expectedStatus: [400, 422] });
//
//   Поле expectedStatus автоматически вырезается перед вызовом k6/http,
//   так что в реальный HTTP-запрос оно не попадает.
//   Если фактический статус совпал с ожидаемым — запрос считается ожидаемым
//   и при LOG_ONLY_UNEXPECTED (по умолчанию) НЕ пишется в лог.
//   Если статус не совпал — это неожиданность, и лог пишется всегда
//   (даже если LOG_ONLY_UNEXPECTED включён), через console.error.
//
// Использование: замени во всех UC-файлах
//   import http from 'k6/http';
//   →
//   import http from './helper/http_logger.js';

import http from 'k6/http';

const ENABLED            = __ENV.LOG_HTTP            !== '0';
const LOG_ONLY_UNEXPECTED= __ENV.LOG_ONLY_UNEXPECTED !== '0';   // включено по умолчанию
const LOG_REQ_BODY       = __ENV.LOG_REQ_BODY        !== '0';
const LOG_RES_BODY       = __ENV.LOG_RES_BODY        !== '0';
const LOG_HEADERS        = __ENV.LOG_HEADERS         !== '0';   // включено по умолчанию
const LOG_AUTH_FULL      = __ENV.LOG_AUTH_FULL       === '1';   // маскировать по умолчанию
const MAX_BODY           = parseInt(__ENV.LOG_MAX_BODY || '500', 10);

const SEP = '─'.repeat(60);

function truncate(str) {
  if (!str) return '';
  const s = String(str);
  return s.length > MAX_BODY ? s.slice(0, MAX_BODY) + ` …[+${s.length - MAX_BODY} chars]` : s;
}

function formatBody(raw) {
  if (raw === null || raw === undefined || raw === '') return '(empty)';
  const s = String(raw);
  try {
    const parsed = JSON.parse(s);
    const pretty = JSON.stringify(parsed, null, 2);
    return truncate(pretty);
  } catch (_) {
    return truncate(s);
  }
}

function maskHeaderValue(key, value) {
  const k = key.toLowerCase();
  if (k === 'authorization') {
    if (LOG_AUTH_FULL) return value;
    // Сохраняем схему (Bearer / Basic / …), маскируем токен
    const space = String(value).indexOf(' ');
    if (space === -1) return '***';
    const scheme = String(value).slice(0, space);
    const token  = String(value).slice(space + 1);
    const visible = token.length > 8 ? token.slice(0, 4) + '…' + token.slice(-4) : '***';
    return `${scheme} ${visible}`;
  }
  return value;
}

function formatHeaders(headers) {
  if (!headers || typeof headers !== 'object') return '    (none)';
  const entries = Object.entries(headers);
  if (entries.length === 0) return '    (none)';
  return entries
    .map(([k, v]) => `    ${k}: ${maskHeaderValue(k, v)}`)
    .join('\n');
}

function indent(text) {
  return String(text).replace(/\n/g, '\n    ');
}

// Определяет, является ли ответ "ожидаемым".
// Если expectedStatus задан явно (число или массив чисел) — сравниваем с ним.
// Иначе по умолчанию ожидаемым считается любой 2xx.
function isExpected(res, expectedStatus) {
  if (expectedStatus !== undefined && expectedStatus !== null) {
    if (Array.isArray(expectedStatus)) {
      return expectedStatus.includes(res.status);
    }
    return res.status === expectedStatus;
  }
  return res.status >= 200 && res.status < 300;
}

// Вырезает expectedStatus из params, чтобы не передавать его дальше в k6/http.
function extractExpected(params) {
  if (!params || typeof params !== 'object' || !('expectedStatus' in params)) {
    return { cleanParams: params, expectedStatus: undefined };
  }
  const { expectedStatus, ...cleanParams } = params;
  return { cleanParams, expectedStatus };
}

function logExchange(method, url, body, params, res, expectedStatus) {
  if (!ENABLED) return;

  const expected = isExpected(res, expectedStatus);

  // По умолчанию пишем в лог только неожиданные запросы/ответы.
  if (LOG_ONLY_UNEXPECTED && expected) return;

  const icon   = expected ? '✓' : '✗';
  const timing = `${res.timings.duration.toFixed(0)}ms`;

  const lines = [
    SEP,
    `${icon} ${method} ${url}`,
    `  Status  : ${res.status} | Time : ${timing}`,
  ];

  // Заголовки запроса — всегда, если не отключены
  if (LOG_HEADERS) {
    lines.push(`  Headers :`);
    lines.push(formatHeaders(params && params.headers));
  }

  // Тело запроса — всегда секция, "(empty)" если нет тела
  if (LOG_REQ_BODY) {
    lines.push(`  Req body:`);
    lines.push(`    ${indent(formatBody(body))}`);
  }

  // Тело ответа — всегда секция, "(empty)" если нет тела
  if (LOG_RES_BODY) {
    lines.push(`  Res body:`);
    lines.push(`    ${indent(formatBody(res.body))}`);
  }

  const msg = lines.join('\n');

  if (expected) {
    console.log(msg);
  } else {
    console.error(msg);
  }
}

function wrap(method, fn) {
  return function (url, bodyOrParams, params) {
    const hasBody = method !== 'GET' && method !== 'DELETE';

    if (hasBody) {
      const { cleanParams, expectedStatus } = extractExpected(params);
      const res = fn(url, bodyOrParams, cleanParams);
      logExchange(method, url, bodyOrParams, cleanParams, res, expectedStatus);
      return res;
    } else {
      // GET / DELETE: второй аргумент — params, не body
      const { cleanParams, expectedStatus } = extractExpected(bodyOrParams);
      const res = fn(url, cleanParams);
      logExchange(method, url, null, cleanParams, res, expectedStatus);
      return res;
    }
  };
}

function wrappedDel(url, body, params) {
  const { cleanParams, expectedStatus } = extractExpected(params);
  const res = http.del(url, body, cleanParams);
  logExchange('DELETE', url, body || null, cleanParams, res, expectedStatus);
  return res;
}

export const get   = wrap('GET',   http.get);
export const post  = wrap('POST',  http.post);
export const put   = wrap('PUT',   http.put);
export const patch = wrap('PATCH', http.patch);
export const del   = wrappedDel;

export default { get, post, put, patch, del };