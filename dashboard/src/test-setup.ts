// Ogni test parte dall'indirizzo vuoto: la navigazione a frammento non trascina stato fra i test.
import { beforeEach } from 'vitest';
import { resetRouterForTests } from './ui/router';

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  resetRouterForTests();
});
