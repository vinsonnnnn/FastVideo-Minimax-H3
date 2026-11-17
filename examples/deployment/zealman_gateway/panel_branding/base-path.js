/* Scope the exported panel to one path without changing its backend protocol. */
(() => {
  const base = document.currentScript.dataset.basePath;
  const prefix = base.slice(0, -1);
  window.__LICHTV_BASE_PATH__ = base;

  // Browsers expose getRandomValues on HTTP, but randomUUID requires HTTPS.
  if (window.crypto && !window.crypto.randomUUID) {
    window.crypto.randomUUID = () => {
      const bytes = window.crypto.getRandomValues(new Uint8Array(16));
      bytes[6] = (bytes[6] & 15) | 64;
      bytes[8] = (bytes[8] & 63) | 128;
      const hex = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('');
      return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    };
  }

  function scopedURL(value) {
    if (value == null) return value;
    try {
      const url = new URL(String(value), window.location.href);
      if (!['http:', 'https:', 'ws:', 'wss:'].includes(url.protocol)) return value;
      if (url.host !== window.location.host) return value;
      if (url.pathname === prefix || url.pathname.startsWith(base)) return value;
      url.pathname = prefix + url.pathname;
      return url.href;
    } catch {
      return value;
    }
  }

  const fetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    if (input instanceof Request) {
      const url = scopedURL(input.url);
      return fetch(url === input.url ? input : new Request(url, input), init);
    }
    return fetch(scopedURL(input), init);
  };

  const openRequest = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...args) {
    return openRequest.call(this, method, scopedURL(url), ...args);
  };

  const WebSocket = window.WebSocket;
  window.WebSocket = class extends WebSocket {
    constructor(url, protocols) {
      if (protocols === undefined) super(scopedURL(url));
      else super(scopedURL(url), protocols);
    }
  };
  if (window.EventSource) {
    const EventSource = window.EventSource;
    window.EventSource = class extends EventSource {
      constructor(url, options) { super(scopedURL(url), options); }
    };
  }

  const attributes = new Set(['src', 'href', 'poster', 'action', 'xlink:href']);
  const setAttribute = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function(name, value) {
    return setAttribute.call(this, name, attributes.has(name.toLowerCase()) ? scopedURL(value) : value);
  };
  const setAttributeNS = Element.prototype.setAttributeNS;
  Element.prototype.setAttributeNS = function(namespace, name, value) {
    return setAttributeNS.call(this, namespace, name, attributes.has(name.toLowerCase()) ? scopedURL(value) : value);
  };
  for (const [type, names] of [
    [HTMLImageElement, ['src']], [HTMLMediaElement, ['src']],
    [HTMLVideoElement, ['poster']], [HTMLSourceElement, ['src']],
    [HTMLScriptElement, ['src']], [HTMLLinkElement, ['href']],
    [HTMLAnchorElement, ['href']], [HTMLIFrameElement, ['src']],
    [HTMLFormElement, ['action']],
  ]) {
    for (const name of names) {
      const descriptor = Object.getOwnPropertyDescriptor(type.prototype, name);
      if (!descriptor?.set || !descriptor.configurable) continue;
      Object.defineProperty(type.prototype, name, {
        ...descriptor,
        set(value) { descriptor.set.call(this, scopedURL(value)); },
      });
    }
  }

  const innerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
  Object.defineProperty(Element.prototype, 'innerHTML', {
    ...innerHTML,
    set(value) {
      const html = typeof value === 'string'
        ? value.replace(/(\b(?:src|href|poster|action)\s*=\s*["'])(\/[^"']*)/gi,
          (_, attribute, url) => attribute + scopedURL(url))
        : value;
      innerHTML.set.call(this, html);
    },
  });

  const openWindow = window.open.bind(window);
  window.open = (url, ...args) => openWindow(scopedURL(url), ...args);
})();
