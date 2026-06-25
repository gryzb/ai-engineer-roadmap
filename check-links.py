#!/usr/bin/env python3
"""Repeatable link-liveness check for the AI Engineer Roadmap.
Usage: python3 check-links.py [path-to-html]   (default: index.html)
Classifies every external URL as OK / REDIRECT / BLOCKED / DEAD / UNREACHABLE.
Exit code is non-zero if any DEAD (404/410) links are found."""
import sys, re, ssl, urllib.request, urllib.error, concurrent.futures as cf

path = sys.argv[1] if len(sys.argv) > 1 else 'index.html'
html = open(path, encoding='utf-8').read()
urls = sorted(set(re.findall(r'https?://[^\s"\'<>)]+', html)))
# ignore font/asset CDNs that are infra, not content (still check fonts.googleapis once)
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'

def check(u):
    req = urllib.request.Request(u, method='GET', headers={'User-Agent': UA, 'Accept':'*/*'})
    try:
        r = urllib.request.urlopen(req, timeout=12, context=ctx)
        final = r.geturl(); code = r.getcode(); r.close()
        if final.rstrip('/') != u.rstrip('/'):
            return ('REDIRECT', u, str(code)+' -> '+final)
        return ('OK', u, str(code))
    except urllib.error.HTTPError as e:
        if e.code in (401,403,405,406,429,503): return ('BLOCKED', u, str(e.code))
        if e.code in (404,410): return ('DEAD', u, str(e.code))
        return ('OTHER', u, str(e.code))
    except Exception as e:
        return ('UNREACHABLE', u, type(e).__name__)

print('Checking %d unique URLs from %s\n' % (len(urls), path))
results = []
with cf.ThreadPoolExecutor(max_workers=12) as ex:
    for r in ex.map(check, urls): results.append(r)

order = ['DEAD','UNREACHABLE','OTHER','REDIRECT','BLOCKED','OK']
buckets = {k: [] for k in order}
for status, u, info in results: buckets[status].append((u, info))
for k in order:
    if not buckets[k]: continue
    print('=== %s (%d) ===' % (k, len(buckets[k])))
    for u, info in sorted(buckets[k]):
        print('  [%s] %s' % (info, u))
    print()

dead = len(buckets['DEAD'])
print('SUMMARY:', ', '.join('%s=%d'%(k,len(buckets[k])) for k in order))
sys.exit(1 if dead else 0)
