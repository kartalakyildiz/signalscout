NOISY_HOMEPAGE_HTML = """
<html>
<head>
<title>Acme Corp - Home</title>
<style>body { color: red; }</style>
<script>console.log("tracking pixel");</script>
</head>
<body>
<nav><a href="/about">About</a><a href="/careers">Careers</a></nav>
<header><h1>Welcome to Acme Corp</h1></header>
<main>
<h2>We build rockets</h2>
<p>Acme Corp is hiring a Head of AI to lead our new machine learning platform.</p>
<ul>
<li>Founded in 2010</li>
<li>Offices in Austin and Berlin</li>
</ul>
</main>
<footer><p>&copy; 2026 Acme Corp. All rights reserved.</p></footer>
<noscript>Please enable JavaScript.</noscript>
</body>
</html>
"""

THIN_JS_SHELL_HTML = """
<html>
<head><title>App</title></head>
<body>
<div id="root"></div>
<script src="/app.js"></script>
</body>
</html>
"""
