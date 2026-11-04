import settings from '../site/config.json' with { type: 'json' };

export function destinationFor(requestURL) {
  const incoming = new URL(requestURL);
  const destination = new URL(settings.url);
  destination.pathname = incoming.pathname.replace(/^\/open-arcana(?=\/|$)/, '') || '/';
  destination.search = incoming.search;
  return destination.href;
}

export default {
  fetch(request) {
    return new Response(null, {
      status: 301,
      headers: {
        Location: destinationFor(request.url),
        'Cache-Control': 'public, max-age=3600',
        'Access-Control-Allow-Origin': '*',
      },
    });
  },
};
