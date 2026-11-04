import test from 'node:test';
import assert from 'node:assert/strict';
import redirect, { destinationFor } from '../scripts/legacy_redirect.mjs';

test('legacy host redirects to the branded origin with filters intact', () => {
  assert.equal(destinationFor('https://open-arcana.cor-ling.workers.dev/?method=leak&history=origins_before_1900'),
    'https://open-arcana.pages.dev/?method=leak&history=origins_before_1900');
});

test('old repository prefix redirects directly to the corresponding page', () => {
  for (const path of ['/open-arcana', '/open-arcana/']) {
    assert.equal(destinationFor('https://old.example' + path), 'https://open-arcana.pages.dev/');
  }
  assert.equal(destinationFor('https://old.example/open-arcana/records/DISC-0088/?q=test'),
    'https://open-arcana.pages.dev/records/DISC-0088/?q=test');
  assert.equal(destinationFor('https://old.example/open-arcanabot/'), 'https://open-arcana.pages.dev/open-arcanabot/');
});

test('path and query cannot choose another redirect host', () => {
  for (const path of ['//example.org/secret', '/open-arcana//example.org/', '/%2f%2fexample.org/?next=https://example.org/']) {
    assert.equal(new URL(destinationFor('https://old.example' + path)).origin, 'https://open-arcana.pages.dev');
  }
});

test('HTTP response is permanent and public without proxying content', () => {
  const response = redirect.fetch(new Request('https://old.example/data.json'));
  assert.equal(response.status, 301);
  assert.equal(response.headers.get('Location'), 'https://open-arcana.pages.dev/data.json');
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), '*');
  assert.equal(response.body, null);
});
