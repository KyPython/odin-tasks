'use strict';

// A Pa11y browser runner. Keep run self-contained: Pa11y stringifies it.
module.exports = {
  supports: '^10.0.0',
  scripts: [],
  run: async () => {
    const navigation = window.performance.getEntriesByType('navigation')[0];
    const status = navigation && navigation.responseStatus;
    if (!Number.isInteger(status) || status < 200 || status >= 300) {
      throw new Error(`Expected a successful document response; navigation HTTP status was ${status}.`);
    }
    return [];
  }
};
