/**
 * Shared API client helpers for GolfMike frontend.
 * Fetches the API key once from /api/client-config and injects it as
 * X-API-Key header on all /v1/ calls.
 */
(function (global) {
  let _key = null;
  let _pending = null;

  async function _loadKey() {
    if (_key !== null) return _key;
    if (_pending) return _pending;
    _pending = fetch('/api/client-config')
      .then(r => r.json())
      .then(c => { _key = c.api_key || ''; return _key; })
      .catch(() => { _key = ''; return _key; });
    return _pending;
  }

  /** Return headers object with X-API-Key set (once key is loaded). */
  async function apiHeaders() {
    const key = await _loadKey();
    return key ? { 'X-API-Key': key } : {};
  }

  /**
   * drop-in replacement for fetch() that auto-injects the API key for /v1/ paths.
   * For non-/v1/ paths behaves identically to native fetch().
   */
  async function apiFetch(url, options) {
    options = options || {};
    if (typeof url === 'string' && url.startsWith('/v1/')) {
      const headers = await apiHeaders();
      options.headers = Object.assign({}, options.headers || {}, headers);
    }
    return fetch(url, options);
  }

  global.GolfMikeAPI = { apiHeaders, apiFetch };
})(window);
